"""Deterministic planning logic: budget maths, verification and rendering.

Nothing in this module calls an LLM. Numbers, flights, place names, distances
and sources shown to the user are produced here from tool results and the
knowledge base, so they can be unit-tested (see tests/test_planning.py).
"""
import math
import re
from collections import Counter

from knowledge import place_index, distance_km

TIERS = ["luxury", "mid", "budget"]          # most to least expensive
LONG_DRIVE_KM = 30                           # one-way from base: flag it
MAX_DAY_TRIP_KM = 80                         # one-way from base: drop it
DEFAULT_DAYS = 4
DEFAULT_TRAVELLERS = 1

ENTRY_DOCS_RE = re.compile(r"\b(passports?|visas?|e-?visas?|immigration|customs)\b", re.I)
# Airline-style flight numbers such as "6E 123", "AI-681", "QF456". Excludes NH/SH road names.
FLIGHT_NO_RE = re.compile(r"\b(?!NH|SH)([A-Z][A-Z0-9]|[0-9][A-Z])\s?-?(\d{2,4})\b")


def inr(n):
    """Indian digit grouping: 300000 -> ₹3,00,000."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        s = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", s[:-3]) + "," + s[-3:]
    return ("-" if n < 0 else "") + "₹" + s


# --------------------------------------------------------------------------- #
# Trip details / clarification
# --------------------------------------------------------------------------- #
REQUIRED = {
    "destination": "where you'd like to go",
    "origin": "where you're starting from",
    "days": "how many days",
    "travellers": "how many people are travelling",
    "budget_inr": "your total budget (₹)",
}


def missing_fields(trip):
    return [k for k in REQUIRED if not trip.get(k)]


def clarification_message(trip):
    dest = trip.get("destination") or "your trip"
    asks = [REQUIRED[k] for k in missing_fields(trip)]
    lines = [f"Happy to plan {dest}! Before I do, could you tell me:"]
    lines += [f"- {a}" for a in asks]
    lines.append("- travel dates (optional - prices change a lot by season)")
    lines.append("\nOr reply **\"assume\"** and I'll plan with defaults and list every assumption at the top.")
    return "\n".join(lines)


def apply_defaults(trip):
    """Fill gaps with defaults and return (trip, assumptions)."""
    trip = dict(trip)
    assumptions = []
    if not trip.get("days"):
        trip["days"] = DEFAULT_DAYS
        assumptions.append(f"Trip length not given - assumed **{DEFAULT_DAYS} days**.")
    if not trip.get("travellers"):
        trip["travellers"] = DEFAULT_TRAVELLERS
        assumptions.append(f"Number of travellers not given - assumed **{DEFAULT_TRAVELLERS}**.")
    if not trip.get("budget_inr"):
        assumptions.append("No budget given - using **mid-range** prices.")
    elif not trip.get("budget_is_per_person"):
        assumptions.append(f"Budget of {inr(trip['budget_inr'])} treated as the **total for the whole group**.")
    if not trip.get("origin"):
        assumptions.append("Starting point not given - flights and travel-to-destination are skipped.")
    if not trip.get("start_date"):
        assumptions.append("No dates given - prices are indicative and vary by season.")
    return trip, assumptions


def is_domestic(trip):
    """True / False only when both countries are known; None when unsure."""
    a, b = (trip.get("origin_country") or "").strip().lower(), (trip.get("destination_country") or "").strip().lower()
    if not a or not b:
        return None
    return a == b


# --------------------------------------------------------------------------- #
# Budget - always summed in code
# --------------------------------------------------------------------------- #
def _item(name, basis, unit, qty, source):
    return {"item": name, "basis": basis, "unit_inr": int(unit), "qty": int(qty),
            "total_inr": int(unit) * int(qty), "source": source}


def compute_budget_from_kb(kb, days, travellers, tier, place_ids):
    prices = kb["prices_inr"]
    src = prices.get("_source", "knowledge base")
    nights = max(days - 1, 0)
    rooms = math.ceil(travellers / 2)
    items = [
        _item(f"Accommodation ({tier})", f"per room per night × {rooms} room(s) × {nights} night(s)",
              prices["room_per_night"][tier], rooms * nights, src),
        _item(f"Food ({tier})", f"per person per day × {travellers} × {days} day(s)",
              prices["food_per_person_day"][tier], travellers * days, src),
        _item(f"Local transport ({tier})", f"per group per day × {days} day(s)",
              prices["local_transport_day"][tier], days, src),
    ]
    places = place_index(kb)
    unknown_fees = []
    for pid in dict.fromkeys(place_ids):                  # unique, keep order
        p = places.get(pid)
        if not p:
            continue
        if p["fee_inr"] is None:
            unknown_fees.append(p["name"])
        elif p["fee_inr"] > 0:
            items.append(_item(f"Entry: {p['name']}", f"per person × {travellers}",
                               p["fee_inr"], travellers, p["source"] or "knowledge base"))
    return _finish_budget(items, travellers, unknown_fees, estimated=False)


def compute_budget_from_estimates(cost_items, travellers):
    """Fallback when no knowledge base exists: LLM-proposed items, summed in code, flagged as estimates."""
    items = []
    for c in cost_items:
        qty = c["qty"] * (travellers if c["per_person"] else 1)
        basis = f"per person × {travellers} × {c['qty']}" if c["per_person"] else f"per group × {c['qty']}"
        items.append(_item(c["item"], basis, c["unit_inr"], qty, "AI estimate - unverified"))
    return _finish_budget(items, travellers, [], estimated=True)


def _finish_budget(items, travellers, unknown_fees, estimated):
    total = sum(i["total_inr"] for i in items)
    return {"items": items, "total_inr": total, "per_person_inr": round(total / max(travellers, 1)),
            "travellers": travellers, "unknown_fees": unknown_fees, "estimated": estimated}


def choose_tier(kb, days, travellers, budget_inr, place_ids):
    """Most comfortable tier whose computed total fits the budget."""
    if not budget_inr:
        return "mid", compute_budget_from_kb(kb, days, travellers, "mid", place_ids)
    for tier in TIERS:
        b = compute_budget_from_kb(kb, days, travellers, tier, place_ids)
        if b["total_inr"] <= budget_inr:
            return tier, b
    return "budget", compute_budget_from_kb(kb, days, travellers, "budget", place_ids)


# --------------------------------------------------------------------------- #
# Verifier
# --------------------------------------------------------------------------- #
def _scrub(text, domestic, allowed_flights, warnings, where):
    if not text:
        return text
    if domestic and ENTRY_DOCS_RE.search(text):
        warnings.append(f"Removed passport/visa text from {where} (domestic trip).")
        return ""
    for m in FLIGHT_NO_RE.finditer(text):
        code = f"{m.group(1)}{m.group(2)}"
        if code not in allowed_flights:
            warnings.append(f"Removed {where}: it mentioned flight '{m.group(0)}', which is not in the API results.")
            return ""
    return text


def verify_plan(plan, kb, trip, flights):
    """Check the LLM plan against tool data and the knowledge base.

    Returns (clean_plan, warnings). Anything unverifiable is removed or flagged.
    """
    warnings = []
    domestic = is_domestic(trip) is True
    allowed_flights = {f["flight"].replace(" ", "").replace("-", "") for f in flights}
    places = place_index(kb)
    regions = kb["regions"] if kb else {}
    wanted_days = trip["days"]

    days = sorted(plan.get("days", []), key=lambda d: d["day"])
    if len(days) > wanted_days:
        warnings.append(f"Planner returned {len(days)} days; trimmed to the requested {wanted_days}.")
        days = days[:wanted_days]
    elif len(days) < wanted_days:
        warnings.append(f"Planner returned only {len(days)} of {wanted_days} days.")

    clean_days, unknown_dist = [], []
    for d in days:
        acts = []
        base = d.get("base_region")
        if kb:
            if base not in regions:
                regs = [places[a]["region"] for a in d.get("activities", []) if a in places]
                new_base = Counter(regs).most_common(1)[0][0] if regs else next(iter(regions))
                warnings.append(f"Day {d['day']}: unknown base '{base}', using '{new_base}'.")
                base = new_base
            for a in d.get("activities", []):
                p = places.get(a)
                if not p:
                    warnings.append(f"Day {d['day']}: removed '{a}' - not in the verified knowledge base.")
                    continue
                dist = distance_km(kb, base, p)
                if dist is None:
                    unknown_dist.append(p["name"])
                elif dist > MAX_DAY_TRIP_KM:
                    warnings.append(f"Day {d['day']}: removed {p['name']} - about {dist} km from base, too far for a day plan.")
                    continue
                acts.append({"id": a, "name": p["name"], "region": p["region"], "km_from_base": dist,
                             "source": p["source"], "verified": True})
                if dist is not None and dist > LONG_DRIVE_KM:
                    warnings.append(f"Day {d['day']}: {p['name']} is ~{dist} km each way from the base - long drive.")
        else:
            acts = [{"id": None, "name": a, "region": None, "km_from_base": None, "source": None, "verified": False}
                    for a in d.get("activities", [])]
        note = _scrub((d.get("note") or "")[:200], domestic, allowed_flights, warnings, f"Day {d['day']} note")
        clean_days.append({"day": d["day"], "base_region": base, "activities": acts, "note": note})

    if unknown_dist:
        warnings.append("Distance not verified for: " + ", ".join(dict.fromkeys(unknown_dist)) + ".")
    no_source = [a["name"] for d in clean_days for a in d["activities"] if a["verified"] and not a["source"]]
    if no_source:
        warnings.append("No source on file for: " + ", ".join(dict.fromkeys(no_source)) + " - check details locally.")
    if kb:
        bases = [d["base_region"] for d in clean_days]
        moves = sum(1 for a, b in zip(bases, bases[1:]) if a != b)
        if moves > 1:
            warnings.append(f"Plan changes base {moves} times - consider fewer hotel moves.")
    else:
        warnings.append("No verified knowledge base for this destination: places are AI suggestions - check them before booking.")

    return {"days": clean_days}, warnings


def check_budget_math(budget):
    """Independent re-check that the shown total equals the sum of its items."""
    return budget["total_inr"] == sum(i["unit_inr"] * i["qty"] for i in budget["items"])


# --------------------------------------------------------------------------- #
# Rendering - the final user-facing text is built here, not by the LLM
# --------------------------------------------------------------------------- #
class _Sources:
    def __init__(self):
        self.urls = []

    def cite(self, url):
        if not url:
            return ""
        if url not in self.urls:
            self.urls.append(url)
        return f" [{self.urls.index(url) + 1}]"


def render_response(trip, assumptions, kb, flights, flight_errors, plan, budget, tier,
                    hotel_results, warnings, mock=False, flight_source="AviationStack", web_source="Tavily"):
    src = _Sources()
    domestic = is_domestic(trip)
    regions = kb["regions"] if kb else {}
    auto = bool(kb and kb.get("auto_built"))
    out = []

    if mock:
        out.append("> ⚠️ **MOCK MODE** - flights, places, hotels and locations below are fake test data.\n")
    title_from = f"{trip['origin']} → " if trip.get("origin") else ""
    out.append(f"# {trip['days']}-day trip: {title_from}{trip.get('destination') or 'your destination'}")
    out.append(f"**Travellers:** {trip['travellers']} · **Style:** {tier}"
               + (f" · **Dates:** {trip['start_date']}" if trip.get("start_date") else ""))

    if assumptions:
        out.append("\n## Assumptions")
        out += [f"- {a}" for a in assumptions]

    # --- Getting there -----------------------------------------------------
    out.append("\n## Getting there")
    if flights:
        out.append(f"Flights seen on this route ({flight_source}). These are today's flights, "
                   "**not fares or availability for your dates**.\n")
        out.append("| Flight | Airline | From | To | Scheduled (UTC) | Status |")
        out.append("|---|---|---|---|---|---|")
        for f in flights:
            out.append(f"| {f['flight']} | {f['airline']} | {f['from']} | {f['to']} | {f['scheduled']} | {f['status']} |")
    else:
        reason = f" ({'; '.join(flight_errors)})" if flight_errors else ""
        out.append(f"Live flight data unavailable{reason}. Check airline sites or a fare-comparison site.")
    out.append("")
    if kb:
        for a in kb.get("access", []):
            out.append(f"- {a['text']}{src.cite(a.get('source'))}")
    if domestic is False:
        out.append("- International trip: check entry and visa requirements for your nationality on official government sites.")

    # --- Day by day --------------------------------------------------------
    out.append("\n## Day-by-day")
    for d in plan["days"]:
        base = regions.get(d["base_region"], {}).get("label", d["base_region"] or "-")
        out.append(f"\n### Day {d['day']} · Base: {base}")
        if not d["activities"]:
            out.append("- Free day / rest")
        for a in d["activities"]:
            if not a["verified"]:
                out.append(f"- {a['name']} *(unverified - please check)*")
                continue
            km = a["km_from_base"]
            if km is None:
                dist = "distance not verified"
            elif km == 0:
                dist = "in base area"
            else:
                dist = f"~{km} km from {'centre' if auto else 'base'}"
            out.append(f"- {a['name']} ({dist}){src.cite(a['source'])}")
        if d["note"]:
            out.append(f"  \n  _{d['note']}_")

    # --- Hotels ------------------------------------------------------------
    out.append("\n## Where to stay")
    if hotel_results:
        out.append(f"Web search results ({web_source}). **Prices and availability are not verified**. Check before booking.\n")
        for h in hotel_results:
            snippet = (h.get("content") or "").strip()
            if len(snippet) > 200:
                snippet = snippet[:200].rsplit(" ", 1)[0] + "..."
            out.append(f"- **{h['title']}**{src.cite(h.get('url'))}" + (f" - {snippet}" if snippet else ""))
    else:
        out.append("Hotel search unavailable. Search a booking site for your base area.")

    # --- Budget ------------------------------------------------------------
    out.append("\n## Budget (calculated in code)")
    if budget["estimated"]:
        out.append("No verified price data for this destination: these are **AI estimates**, summed in code.\n")
    out.append("| Item | Basis | Unit | Qty | Total |")
    out.append("|---|---|---|---|---|")
    for i in budget["items"]:
        out.append(f"| {i['item']} | {i['basis']} | {inr(i['unit_inr'])} | {i['qty']} | {inr(i['total_inr'])} |")
    out.append(f"| **Total (whole group)** | | | | **{inr(budget['total_inr'])}** |")
    out.append(f"| **Per person** | | | | **{inr(budget['per_person_inr'])}** |")
    out.append("")
    notes = []
    if kb and not budget["estimated"]:
        notes.append(f"Prices: {kb['prices_inr'].get('_source', 'knowledge base')}.")
    notes.append("Excludes travel to/from the destination (live fares not available).")
    if budget["unknown_fees"]:
        notes.append("Fees not included (unknown): " + ", ".join(budget["unknown_fees"]) + ".")
    if trip.get("budget_inr"):
        cap = trip["budget_inr"] * (trip["travellers"] if trip.get("budget_is_per_person") else 1)
        diff = cap - budget["total_inr"]
        notes.append(f"Your budget {inr(cap)}: " + (f"**{inr(diff)} left** for travel to/from the destination and extras."
                                                     if diff >= 0 else f"**over by {inr(-diff)}**."))
    out += [f"- {n}" for n in notes]

    # --- Checks ------------------------------------------------------------
    out.append("\n## Checks")
    out.append("- Flights: only rows returned by the API are shown." if flights else "- Flights: none shown (no API data).")
    if not kb:
        out.append("- Places: **not verified** (no knowledge base).")
    elif auto:
        out.append(f"- Places: each one is named in its cited web page and located within "
                   f"{MAX_DAY_TRIP_KM} km of {kb['name']} (built automatically, not hand-checked).")
    else:
        out.append("- Places: from the hand-checked knowledge base.")
    out.append("- Budget total re-checked against its items: " + ("OK" if check_budget_math(budget) else "**MISMATCH**"))
    if domestic:
        out.append("- Domestic trip: no passport/visa content.")
    out += [f"- ⚠️ {w}" for w in warnings]

    if src.urls:
        out.append("\n## Sources")
        out += [f"{n}. {u}" for n, u in enumerate(src.urls, 1)]

    return "\n".join(out)
