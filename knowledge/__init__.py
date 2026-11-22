"""Destination knowledge.

- Hand-written files (e.g. goa.json) in this folder are used first.
- Any other destination gets a knowledge base built automatically by
  knowledge.builder (web search + geocoding) and cached in knowledge/cache/.

Distances: if both points have coordinates, straight-line distance × ROAD_FACTOR;
otherwise the file's region_distances_km table.
"""
import json
from functools import lru_cache
from pathlib import Path

from providers import haversine_km

KB_DIR = Path(__file__).parent
ROAD_FACTOR = 1.3     # roads are rarely straight; rough conversion from straight-line km


@lru_cache(maxsize=None)
def _local_kbs():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(KB_DIR.glob("*.json"))]


def find_local_kb(*texts):
    """Hand-written knowledge base whose alias appears in any of the texts, else None."""
    haystack = " ".join(t.lower() for t in texts if t)
    for kb in _local_kbs():
        if any(alias in haystack for alias in kb["aliases"]):
            return kb
    return None


def place_index(kb):
    return {p["id"]: p for p in kb["places"]} if kb else {}


def _coords(obj):
    if obj and obj.get("lat") is not None and obj.get("lon") is not None:
        return obj["lat"], obj["lon"]
    return None


def region_distance(kb, a, b):
    if a == b:
        return 0
    d = kb.get("region_distances_km", {})
    return d.get(f"{a}|{b}", d.get(f"{b}|{a}"))


def distance_km(kb, base_region, place):
    """Approx. road km from a base region to a place, or None if unknown."""
    region = kb["regions"].get(base_region)
    a, b = _coords(region), _coords(place)
    if a and b:
        return round(haversine_km(a, b) * ROAD_FACTOR)
    return region_distance(kb, base_region, place.get("region"))
