import os
import requests


def search_flights(dep_iata, arr_iata):
    """Live flights on a route from Aviationstack.

    Returns {"flights": [dict, ...], "error": str | None}. The flight dicts are
    passed straight to the renderer, so every flight shown to the user comes
    from this API response and nothing else.
    """
    if not dep_iata or not arr_iata:
        return {"flights": [], "error": "origin or destination airport unknown"}

    # Read at call time so keys from Streamlit secrets (set after import) are picked up.
    params = {"access_key": os.getenv("AVIATIONSTACK_API"),"dep_iata": dep_iata, "arr_iata": arr_iata, "limit": 5}
    try:
        data = requests.get("https://api.aviationstack.com/v1/flights", params=params, timeout=15).json()
    except Exception as e:
        return {"flights": [], "error": str(e)}

    if "error" in data:
        err = data["error"]
        return {"flights": [], "error": err.get("message", str(err)) if isinstance(err, dict) else str(err)}

    flights = []
    for f in data.get("data") or []:
        dep = f.get("departure") or {}
        arr = f.get("arrival") or {}
        flights.append({
            "flight": (f.get("flight") or {}).get("iata") or "-",
            "airline": (f.get("airline") or {}).get("name") or "-",
            "from": dep.get("iata") or dep_iata,
            "to": arr.get("iata") or arr_iata,
            "scheduled": dep.get("scheduled") or "-",
            "status": f.get("flight_status") or "-",
        })
    return {"flights": flights[:5], "error": None}
