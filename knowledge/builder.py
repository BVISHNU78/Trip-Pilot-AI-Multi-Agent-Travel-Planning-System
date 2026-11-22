"""Build a knowledge base for any destination that has no hand-written file.

A place is accepted only if
  1. it is named in the web search result it was extracted from (that URL becomes its source), and
  2. it geocodes to within MAX_PLACE_RADIUS_KM of the destination centre.
Everything else is dropped and reported, so the planner can never be offered
an invented attraction or one in another region (e.g. Diu for a Goa trip).
"""
import json
import re
from datetime import date
from pathlib import Path

import providers
from knowledge import find_local_kb, distance_km

CACHE_DIR = Path(__file__).parent / "cache"
MAX_PLACE_RADIUS_KM = 80      # approx. road km from the centre; matches planning.MAX_DAY_TRIP_KM
MAX_PLACES = 12


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


def mentioned(name, text):
    """True if the name (or most of its significant words) appears in the text."""
    n, t = _norm(name).strip(), _norm(text)
    if n and n in t:
        return True
    words = [w for w in n.split() if len(w) > 3]
    return bool(words) and sum(w in t.split() for w in words) / len(words) >= 0.75


def get_kb(destination, country=None, user_text=""):
    """Return (kb or None, notes). Local file → cache → auto-build."""
    local = find_local_kb(destination, user_text)
    if local:
        return local, []
    if not destination:
        return None, ["No destination identified."]

    cache = CACHE_DIR / f"{slug(destination)}.json"
    if not providers.mock_mode() and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8")), []

    kb, notes = build_kb(destination, country)
    if kb and not providers.mock_mode():
        CACHE_DIR.mkdir(exist_ok=True)
        cache.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")
    return kb, notes


def build_kb(destination, country=None):
    notes = []
    where = f"{destination}, {country}" if country else destination
    try:
        results = providers.web_search(f"top tourist attractions in {where}", max_results=6)
    except Exception as e:
        return None, [f"Could not search for attractions: {e}"]
    if not results:
        return None, ["Web search returned no attractions."]

    try:
        candidates = providers.extract_places(destination, results)
    except Exception as e:
        return None, [f"Could not extract attractions: {e}"]

    center = providers.geocode(where)
    if not center:
        notes.append(f"Could not locate {destination} on the map - distances are not verified.")
    kb = {
        "name": destination, "country": country, "aliases": [destination.lower()],
        "auto_built": True, "built_on": date.today().isoformat(),
        "airports": [], "access": [], "tips": [], "region_distances_km": {},
        "regions": {"center": {"label": f"Central {destination}",
                               "lat": center[0] if center else None, "lon": center[1] if center else None}},
        "places": [],
    }

    seen = set()
    for c in candidates:
        if len(kb["places"]) >= MAX_PLACES:
            break
        pid = slug(c.name)
        if not pid or pid in seen:
            continue
        r = results[c.source] if 0 <= c.source < len(results) else None
        if not r or not mentioned(c.name, f"{r['title']} {r['content']}"):
            notes.append(f"Dropped '{c.name}': not named in its cited search result.")
            continue
        coords = providers.geocode(f"{c.name}, {destination}")
        place = {"id": pid, "name": c.name, "region": "center", "type": c.type, "fee_inr": None,
                 "source": r["url"], "lat": coords[0] if coords else None, "lon": coords[1] if coords else None}
        if center and coords:
            d = distance_km(kb, "center", place)
            if d > MAX_PLACE_RADIUS_KM:
                notes.append(f"Dropped '{c.name}': about {d} km from {destination}, too far.")
                continue
        seen.add(pid)
        kb["places"].append(place)

    if not kb["places"]:
        return None, notes + ["No attraction could be verified."]
    return kb, notes
