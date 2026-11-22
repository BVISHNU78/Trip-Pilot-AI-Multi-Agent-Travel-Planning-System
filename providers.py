"""Every external call (LLM, web search, geocoding, flights) goes through here.

Set TRAVEL_MOCK=1 to replace all of them with deterministic offline fakes:
no API keys, no network, no quota used. The check happens on every call, so
tests can switch it on with os.environ before running the graph.
"""
import hashlib
import math
import os
import re
import time
from datetime import date
from functools import lru_cache

from schemas import Route, Plan, DayPlan, CostItem, PlaceList, PlaceCandidate

GROUNDING_RULE = (
    "If a fact is not in the provided tool results or knowledge base, do not state it. "
    "Never invent flight numbers, prices, hotel names, distances or opening times."
)


def mock_mode():
    return os.getenv("TRAVEL_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}


def source_label(kind):
    if mock_mode():
        return "MOCK data"
    return {"flights": "AviationStack", "web": "Tavily"}[kind]


# =========================================================================== #
# Public interface
# =========================================================================== #
def extract_trip(messages) -> Route:
    return _mock_extract_trip(messages) if mock_mode() else _real_structured(
        Route,
        f"Today is {date.today().isoformat()}. Classify the user's latest message and extract trip details "
        "from the whole conversation. Leave a field null if the user did not state it - never guess days, "
        "budget, travellers or dates.",
        messages)


def chat_reply(messages) -> str:
    if mock_mode():
        return "Hi! Tell me where you'd like to go, from where, for how many days and people, and your budget."
    from langchain_core.messages import SystemMessage
    return _llm().invoke([SystemMessage(content="You are a friendly travel assistant. Reply briefly. If the user "
                                                "hasn't asked for a trip, offer to help plan one. " + GROUNDING_RULE),
                          *messages]).content


def plan_trip(messages, prompt, kb, trip) -> Plan:
    if mock_mode():
        return _mock_plan(kb, trip)
    from langchain_core.messages import HumanMessage
    return _real_structured(Plan, "You are a travel planner that only selects from given data. " + GROUNDING_RULE,
                            [*messages, HumanMessage(content=prompt)])


def extract_places(destination, results) -> list[PlaceCandidate]:
    if mock_mode():
        return _mock_extract_places(results)
    from langchain_core.messages import HumanMessage
    listing = "\n\n".join(f"[{i}] {r['title']}\n{r['content']}" for i, r in enumerate(results))
    out = _real_structured(
        PlaceList,
        "Extract specific, visitable attractions. Use only names that literally appear in the text. " + GROUNDING_RULE,
        [HumanMessage(content=f"Search results about {destination}:\n\n{listing}\n\n"
                              f"List up to 12 attractions in or near {destination}, with the result number.")])
    return out.places


def web_search(query, max_results=5) -> list[dict]:
    """Returns [{"title", "url", "content"}]."""
    if mock_mode():
        return _mock_web_search(query, max_results)
    from tavily import TavilyClient
    key = os.getenv("TAVILY_API") or os.getenv("TAVILY_API_KEY")   # both names are used in deployments
    resp = TavilyClient(api_key=key).search(query=query, max_results=max_results)
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": (r.get("content") or "").strip()}
            for r in resp.get("results", [])]


def geocode(query):
    """Returns (lat, lon) or None."""
    return _mock_geocode(query) if mock_mode() else _real_geocode(query)


def search_flights(dep_iata, arr_iata) -> dict:
    if mock_mode():
        return _mock_flights(dep_iata, arr_iata)
    from tools.flight_tool import search_flights as real
    return real(dep_iata, arr_iata)


# =========================================================================== #
# Real implementations
# =========================================================================== #
@lru_cache(maxsize=1)
def _llm():
    from langchain_groq import ChatGroq
    # Linux (Streamlit Cloud) env vars are case-sensitive; accept the old lowercase name too.
    return ChatGroq(model="openai/gpt-oss-20b",
                    api_key=os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key"))


def _real_structured(schema, system, messages):
    from langchain_core.messages import SystemMessage
    return _llm().with_structured_output(schema).invoke([SystemMessage(content=system), *messages])


_last_geocode = [0.0]


def _real_geocode(query):
    import requests
    wait = 1.1 - (time.time() - _last_geocode[0])     # Nominatim policy: max 1 request/second
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": query, "format": "json", "limit": 1},
                         headers={"User-Agent": "travel-planner-demo/1.0"}, timeout=15)
        data = r.json()
        return (float(data[0]["lat"]), float(data[0]["lon"])) if data else None
    except Exception:
        return None
    finally:
        _last_geocode[0] = time.time()


# =========================================================================== #
# Mock implementations (deterministic, offline)
# =========================================================================== #
CITY_INFO = {  # name -> (country, IATA)
    "kochi": ("India", "COK"), "cochin": ("India", "COK"), "mumbai": ("India", "BOM"), "delhi": ("India", "DEL"),
    "bengaluru": ("India", "BLR"), "bangalore": ("India", "BLR"), "chennai": ("India", "MAA"),
    "hyderabad": ("India", "HYD"), "goa": ("India", "GOI"), "jaipur": ("India", "JAI"), "hampi": ("India", None),
    "manali": ("India", None), "diu": ("India", "DIU"), "paris": ("France", "CDG"), "london": ("UK", "LHR"),
    "tokyo": ("Japan", "HND"), "dubai": ("UAE", "DXB"), "bali": ("Indonesia", "DPS"),
    "bangkok": ("Thailand", "BKK"), "singapore": ("Singapore", "SIN"), "new york": ("USA", "JFK"),
}
GREETINGS = {"hi", "hello", "hey", "hii", "thanks", "thank you", "ok", "okay", "good morning", "good evening"}
TRAVEL_WORDS = re.compile(r"\b(trip|travel|plan|visit|tour|itinerary|holiday|vacation|days?|budget|people|"
                          r"persons?|assume|lakhs?)\b|\bto\s+[a-z]", re.I)
ROUTE_STOP = {"trip", "travel", "plan", "go", "going", "way", "days", "day", "a", "the", "me", "want", "like",
              "fly", "holiday", "vacation", "tour", "visit", "trips", "weekend"}
_END = r"(?=\s+(?:for|with|under|in|on|budget|and|within|from)\b|[,.!?]|$)"


def _mock_extract_trip(messages):
    humans = [m.content for m in messages if getattr(m, "type", "") == "human"]
    latest = (humans[-1] if humans else "").strip().lower().rstrip("!.")
    f = {}
    for text in humans:
        t = text.lower()
        m = re.search(rf"\bfrom\s+([a-z][a-z ]*?)\s+to\s+([a-z][a-z ]*?){_END}", t) or \
            re.search(rf"\b([a-z]+)\s+to\s+([a-z][a-z ]*?){_END}", t)
        if m:
            o, d = m.group(1).strip(), m.group(2).strip()
            if o not in ROUTE_STOP:
                f["origin"] = o.title()
            f["destination"] = d.title()
        if m := re.search(r"(\d+)\s*-?\s*days?\b", t):
            f["days"] = int(m.group(1))
        if m := re.search(r"(\d+)\s*(?:people|persons?|person|travell?ers|adults|pax)\b", t):
            f["travellers"] = int(m.group(1))
        elif re.search(r"\bsolo\b", t):
            f["travellers"] = 1
        if m := re.search(r"(\d+(?:\.\d+)?)\s*lakhs?\b", t):
            f["budget_inr"] = int(float(m.group(1)) * 100000)
        elif m := re.search(r"(?:budget|under|within|₹|rs\.?|inr)\s*(?:of\s*)?(\d[\d,]*)\s*(k\b)?", t):
            f["budget_inr"] = int(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1)
        if "per person" in t:
            f["budget_is_per_person"] = True
        if re.search(r"\b(assume|go ahead|you decide)\b", t):
            f["proceed_with_assumptions"] = True

    for side in ("origin", "destination"):
        info = CITY_INFO.get((f.get(side) or "").lower())
        if info:
            f[f"{side}_country"], f[f"{side}_iata"] = info

    is_travel = latest not in GREETINGS and f.get("destination") and any(TRAVEL_WORDS.search(h) for h in humans)
    return Route(intent="travel" if is_travel else "chat", **f)


def _mock_plan(kb, trip):
    days, places = trip["days"], (kb or {}).get("places", [])
    plan_days = []
    for i in range(days):
        chunk = places[2 * i: 2 * i + 2]
        base = chunk[0]["region"] if chunk else next(iter((kb or {}).get("regions", {"center": 0})))
        plan_days.append(DayPlan(day=i + 1, base_region=base, activities=[p["id"] for p in chunk],
                                 note="Easy pace." if chunk else "Free day."))
    costs = []
    if not (kb or {}).get("prices_inr"):
        nights = max(days - 1, 0)
        costs = [CostItem(item="Accommodation (estimate)", unit_inr=3000, qty=nights, per_person=False),
                 CostItem(item="Food (estimate)", unit_inr=1000, qty=days, per_person=True),
                 CostItem(item="Local transport (estimate)", unit_inr=1500, qty=days, per_person=False)]
    return Plan(days=plan_days, estimated_costs=costs)


MOCK_SIGHTS = ["Old Town", "City Museum", "Central Market", "Botanical Garden", "Riverside Promenade",
               "Hilltop Viewpoint"]


def _mock_web_search(query, max_results):
    dest = re.sub(r"^.*\bin\s+", "", query).split(",")[0].strip().title() or "Somewhere"
    if "hotel" in query.lower():
        return [{"title": f"{dest} Mock Hotel {n}", "url": f"https://example.com/mock-hotel-{n}",
                 "content": "Mock search result. Not a real hotel."} for n in range(1, 4)]
    names = [f"{dest} {s}" for s in MOCK_SIGHTS] + [f"{dest} Distant Island"]
    return [{"title": n, "url": f"https://example.com/mock/{_slug(n)}",
             "content": f"{n} is a popular attraction (mock data)."} for n in names][:max(max_results, 7)]


def _mock_extract_places(results):
    out = [PlaceCandidate(name=r["title"], source=i) for i, r in enumerate(results)]
    # A hallucination the builder must reject (named in no result):
    out.append(PlaceCandidate(name="Imaginary Crystal Palace", source=0))
    return out


def _mock_geocode(query):
    parts = [p.strip().lower() for p in query.split(",")]
    countries = {c.lower() for c, _ in CITY_INFO.values()}
    if len(parts) > 1 and parts[-1] in countries:        # "Paris, France" -> "paris"
        parts = parts[:-1]
    dest = parts[-1]
    h = int(hashlib.md5(dest.encode()).hexdigest(), 16)
    lat, lon = (h % 9000) / 100 - 40, (h // 9000 % 26000) / 100 - 120     # deterministic "city centre"
    if len(parts) == 1:
        return lat, lon
    if "distant island" in parts[0]:
        return lat + 5, lon                                               # ~550 km away
    k = int(hashlib.md5(parts[0].encode()).hexdigest(), 16)
    return lat + (k % 200 - 100) / 1000, lon + (k // 200 % 200 - 100) / 1000   # within ~15 km


def _mock_flights(dep, arr):
    if not dep or not arr:
        return {"flights": [], "error": "origin or destination airport unknown"}
    return {"flights": [{"flight": f"MK{n}{len(dep + arr)}", "airline": "MockAir", "from": dep, "to": arr,
                         "scheduled": "2026-01-01T09:00", "status": "scheduled"} for n in (1, 2)],
            "error": None}


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))
