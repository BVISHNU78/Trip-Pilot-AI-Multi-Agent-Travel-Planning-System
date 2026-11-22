"""Travel planner graph.

    router → (chat | clarify | knowledge → flights → planner → hotels → verifier → final)

All external calls go through providers.py. Run with TRAVEL_MOCK=1 to use
offline fakes (no API keys, no network) - that is what the tests do.
"""
import os
import operator
from collections import Counter
from typing import TypedDict, Annotated, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from dotenv import load_dotenv

import planning
import providers
from knowledge import distance_km
from knowledge.builder import get_kb

load_dotenv()

DATABASE_url = os.getenv("DATABASE_url")
HISTORY_WINDOW = 10


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    intent: str
    trip: dict
    assumptions: list
    kb: Optional[dict]
    flights: list
    flight_errors: list
    plan: dict
    tier: str
    hotel_results: list
    budget: dict
    warnings: list


def recent_history(state):
    return state["messages"][-HISTORY_WINDOW:]


# --------------------------------------------------------------------------- #
# Routing
# --------------------------------------------------------------------------- #
def router_agent(state: TravelState):
    try:
        route = providers.extract_trip(recent_history(state))
    except Exception:
        return {"intent": "chat"}
    trip = route.model_dump(exclude={"intent", "proceed_with_assumptions"})
    trip["proceed"] = route.proceed_with_assumptions
    return {"intent": route.intent, "trip": trip}


def route_after_router(state: TravelState):
    if state.get("intent") != "travel":
        return "chat_agent"
    trip = state["trip"]
    if not trip.get("destination") or (planning.missing_fields(trip) and not trip.get("proceed")):
        return "clarify_agent"
    return "knowledge_agent"


def chat_agent(state: TravelState):
    return {"messages": [AIMessage(content=providers.chat_reply(recent_history(state)))]}


def clarify_agent(state: TravelState):
    return {"messages": [AIMessage(content=planning.clarification_message(state["trip"]))]}


# --------------------------------------------------------------------------- #
# Knowledge + tools
# --------------------------------------------------------------------------- #
def knowledge_agent(state: TravelState):
    trip, assumptions = planning.apply_defaults(state["trip"])
    kb, notes = get_kb(trip.get("destination"), trip.get("destination_country"), state.get("user_query", ""))
    return {"trip": trip, "assumptions": assumptions, "kb": kb, "warnings": notes}


def flight_agent(state: TravelState):
    trip, kb = state["trip"], state.get("kb")
    dest_codes = [a["iata"] for a in kb["airports"]] if kb and kb.get("airports") else [trip.get("destination_iata")]
    flights, errors = [], []
    if not trip.get("origin_iata"):
        errors.append("origin airport unknown")
    else:
        for code in filter(None, dest_codes):
            r = providers.search_flights(trip["origin_iata"], code)
            flights += r["flights"]
            if r["error"]:
                errors.append(f"{trip['origin_iata']}→{code}: {r['error']}")
        if not any(dest_codes):
            errors.append("destination airport unknown")
    return {"flights": flights, "flight_errors": errors}


def _kb_prompt(kb):
    lines = []
    for p in kb["places"]:
        km = distance_km(kb, "center", p) if kb.get("auto_built") else None
        extra = f" | ~{km} km from centre" if kb.get("auto_built") and km is not None else ""
        lines.append(f"- {p['id']} | {p['name']} | region={p['region']} | {p['type']}{extra}")
    dists = "\n".join(f"- {k.replace('|', ' ↔ ')}: {v} km" for k, v in kb.get("region_distances_km", {}).items())
    return f"""Regions (use these ids for base_region): {', '.join(kb['regions'])}
Places (use ONLY these ids in activities):
{chr(10).join(lines)}
{('Approx. road distances between regions:' + chr(10) + dists) if dists else ''}
Rules: keep each day's activities within ~{planning.LONG_DRIVE_KM} km of that night's base; prefer one base
for the whole trip (two at most); 2-3 activities per day; do not add places that are not in the list."""


def planner_agent(state: TravelState):
    trip, kb = state["trip"], state.get("kb")
    context = _kb_prompt(kb) if kb else "No verified place list exists for this destination. Suggest only well-known places."
    if not (kb and kb.get("prices_inr")):
        context += "\nNo price data is provided: fill estimated_costs (accommodation, food, local transport, entry fees) in INR."
    prompt = (f"Plan {trip['days']} days in {trip.get('destination')} for {trip['travellers']} traveller(s).\n"
              f"Budget: {trip.get('budget_inr') or 'not given'} INR.\n{context}")
    try:
        plan = providers.plan_trip(recent_history(state), prompt, kb, trip).model_dump()
        return {"plan": plan}
    except Exception as e:
        return {"plan": {"days": [], "estimated_costs": []},
                "warnings": state.get("warnings", []) + [f"Planner failed: {e}"]}


def hotel_agent(state: TravelState):
    kb, trip = state.get("kb"), state["trip"]
    bases = [d.get("base_region") for d in state["plan"].get("days", [])]
    area = trip.get("destination") or ""
    if kb and bases:
        main_base = Counter(bases).most_common(1)[0][0]
        area = kb["regions"].get(main_base, {}).get("label", area)
    try:
        return {"hotel_results": providers.web_search(f"hotels in {area}", max_results=4)}
    except Exception:
        return {"hotel_results": []}


# --------------------------------------------------------------------------- #
# Verifier + final render (no LLM)
# --------------------------------------------------------------------------- #
def verifier_agent(state: TravelState):
    trip, kb = state["trip"], state.get("kb")
    plan, warnings = planning.verify_plan(state["plan"], kb, trip, state.get("flights", []))
    place_ids = [a["id"] for d in plan["days"] for a in d["activities"] if a["id"]]

    if kb and kb.get("prices_inr"):
        cap = trip.get("budget_inr")
        if cap and trip.get("budget_is_per_person"):
            cap *= trip["travellers"]
        tier, budget = planning.choose_tier(kb, trip["days"], trip["travellers"], cap, place_ids)
    else:
        tier = "estimate"
        budget = planning.compute_budget_from_estimates(state["plan"].get("estimated_costs", []), trip["travellers"])

    if not planning.check_budget_math(budget):
        warnings.append("Budget items do not add up to the total.")
    return {"plan": plan, "tier": tier, "budget": budget, "warnings": state.get("warnings", []) + warnings}


def final_agent(state: TravelState):
    text = planning.render_response(
        trip=state["trip"], assumptions=state.get("assumptions", []), kb=state.get("kb"),
        flights=state.get("flights", []), flight_errors=state.get("flight_errors", []),
        plan=state["plan"], budget=state["budget"], tier=state["tier"],
        hotel_results=state.get("hotel_results", []), warnings=state.get("warnings", []),
        mock=providers.mock_mode(), flight_source=providers.source_label("flights"),
        web_source=providers.source_label("web"),
    )
    return {"messages": [AIMessage(content=text)]}


graph = StateGraph(TravelState)
for name, fn in [("router_agent", router_agent), ("chat_agent", chat_agent), ("clarify_agent", clarify_agent),
                 ("knowledge_agent", knowledge_agent), ("flight_agent", flight_agent),
                 ("planner_agent", planner_agent), ("hotel_agent", hotel_agent),
                 ("verifier_agent", verifier_agent), ("final_agent", final_agent)]:
    graph.add_node(name, fn)

graph.add_edge(START, "router_agent")
graph.add_conditional_edges("router_agent", route_after_router, ["chat_agent", "clarify_agent", "knowledge_agent"])
graph.add_edge("chat_agent", END)
graph.add_edge("clarify_agent", END)
graph.add_edge("knowledge_agent", "flight_agent")
graph.add_edge("flight_agent", "planner_agent")
graph.add_edge("planner_agent", "hotel_agent")
graph.add_edge("hotel_agent", "verifier_agent")
graph.add_edge("verifier_agent", "final_agent")
graph.add_edge("final_agent", END)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")   # ₹ and → crash cp1252 Windows consoles

    if providers.mock_mode():
        # Offline: in-memory history, nothing written to MySQL
        from langgraph.checkpoint.memory import MemorySaver
        from contextlib import nullcontext
        saver_ctx = nullcontext(MemorySaver())
        print("MOCK MODE: no APIs are called; all data is fake.")
    else:
        from langgraph.checkpoint.mysql.pymysql import PyMySQLSaver
        saver_ctx = PyMySQLSaver.from_conn_string(DATABASE_url)

    with saver_ctx as checkpointer:
        if hasattr(checkpointer, "setup"):
            checkpointer.setup()
        app = graph.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "user_vishnu_v2"}}

        print("Type 'exit' to quit.")
        while True:
            user_input = input("\nEnter travel request: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break
            result = app.invoke({"messages": [HumanMessage(content=user_input)], "user_query": user_input},
                                config=config)
            print("\nFINAL RESPONSE:\n")
            print(result["messages"][-1].content)
