"""Offline tests - no API keys or network needed.  Run:  python -m pytest tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import planning
from knowledge import find_local_kb

KB = find_local_kb("goa")
DOMESTIC_TRIP = {"origin": "Kochi", "origin_country": "India", "destination": "Goa",
                 "destination_country": "India", "days": 3, "travellers": 2, "budget_inr": 40000}
API_FLIGHTS = [{"flight": "6E123", "airline": "IndiGo", "from": "COK", "to": "GOI",
                "scheduled": "2026-11-22T10:00", "status": "scheduled"}]


def plan(*days):
    return {"days": [{"day": i + 1, "base_region": b, "activities": a, "note": n}
                     for i, (b, a, n) in enumerate(days)]}


def render(trip, p, flights=API_FLIGHTS, flight_errors=()):
    trip, assumptions = planning.apply_defaults(trip)
    clean, warnings = planning.verify_plan(p, KB, trip, flights)
    ids = [a["id"] for d in clean["days"] for a in d["activities"]]
    tier, budget = planning.choose_tier(KB, trip["days"], trip["travellers"], trip.get("budget_inr"), ids)
    text = planning.render_response(trip, assumptions, KB, flights, list(flight_errors), clean, budget,
                                    tier, [], warnings)
    return text, clean, budget, warnings


# --- clarification --------------------------------------------------------- #
def test_vague_request_asks_for_missing_details():
    trip = {"origin": "Kochi", "destination": "Goa"}
    assert set(planning.missing_fields(trip)) == {"days", "travellers", "budget_inr"}
    msg = planning.clarification_message(trip)
    assert "how many days" in msg and "budget" in msg
    assert "passport" not in msg.lower()


def test_assumptions_are_listed_when_defaults_used():
    trip, assumptions = planning.apply_defaults({"origin": "Kochi", "destination": "Goa"})
    assert trip["days"] == planning.DEFAULT_DAYS
    assert any("assumed" in a for a in assumptions)


# --- domestic ---------------------------------------------------------------- #
def test_domestic_trip_has_no_passport_or_visa():
    p = plan(("north", ["calangute_beach"], "Bring your passport and visa."),
             ("north", ["fort_aguada"], ""), ("central", ["basilica_bom_jesus"], ""))
    text, *_ = render(DOMESTIC_TRIP, p)
    assert planning.ENTRY_DOCS_RE.search(text.split("## Checks")[0]) is None


def test_international_trip_gets_generic_entry_note():
    trip = dict(DOMESTIC_TRIP, origin="Dubai", origin_country="UAE")
    text, *_ = render(trip, plan(("north", ["calangute_beach"], "")))
    assert "visa requirements" in text


# --- flights ------------------------------------------------------------------ #
def test_only_api_flights_are_shown():
    p = plan(("north", ["calangute_beach"], "Take flight AI 681 in the morning."))
    text, clean, _, warnings = render(DOMESTIC_TRIP, p)
    assert "6E123" in text
    assert "AI 681" not in text.split("## Checks")[0]
    assert any("AI 681" in w for w in warnings)


def test_no_api_flights_shows_unavailable_message():
    text, *_ = render(DOMESTIC_TRIP, plan(("north", [], "")), flights=[], flight_errors=["timeout"])
    assert "Live flight data unavailable" in text
    assert "| Flight |" not in text


# --- budget ------------------------------------------------------------------- #
def test_budget_total_equals_sum_of_items():
    _, _, budget, _ = render(DOMESTIC_TRIP, plan(("north", ["calangute_beach"], "")))
    assert budget["total_inr"] == sum(i["unit_inr"] * i["qty"] for i in budget["items"])
    assert planning.check_budget_math(budget)


def test_tier_fits_budget_or_warns():
    _, _, budget, _ = render(DOMESTIC_TRIP, plan(("north", [], "")))
    assert budget["total_inr"] <= DOMESTIC_TRIP["budget_inr"]


def test_budget_labels_group_and_per_person():
    text, *_ = render(DOMESTIC_TRIP, plan(("north", [], "")))
    assert "Total (whole group)" in text and "Per person" in text


# --- places & distance --------------------------------------------------------- #
def test_places_outside_kb_are_removed():
    p = plan(("north", ["calangute_beach", "Diu"], ""))
    text, clean, _, warnings = render(DOMESTIC_TRIP, p)
    day_section = text.split("## Day-by-day")[1].split("## Where to stay")[0]
    assert "Diu" not in day_section
    assert any("Diu" in w for w in warnings)


def test_far_places_are_removed_and_long_drives_flagged():
    # Base in the north: Palolem (far south, 85 km) is dropped; Colva (south, 50 km) is flagged.
    p = plan(("north", ["palolem_beach", "colva_beach"], ""))
    _, clean, _, warnings = render(DOMESTIC_TRIP, p)
    names = [a["id"] for a in clean["days"][0]["activities"]]
    assert names == ["colva_beach"]
    assert any("Palolem" in w and "removed" in w for w in warnings)
    assert any("long drive" in w for w in warnings)
