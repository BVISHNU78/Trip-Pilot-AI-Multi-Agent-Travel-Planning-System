"""Evaluation set.

    python eval/run_eval.py          # offline, mock providers (default - no APIs called)
    python eval/run_eval.py --live   # real Groq / Tavily / AviationStack / Nominatim

Uses an in-memory checkpointer, so it never touches your MySQL history.
"""
import os
import re
import sys
import uuid
from pathlib import Path

LIVE = "--live" in sys.argv
os.environ["TRAVEL_MOCK"] = "0" if LIVE else "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from langchain_core.messages import HumanMessage  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

import planning  # noqa: E402
from main import graph  # noqa: E402

app = graph.compile(checkpointer=MemorySaver())


def run(*turns):
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = None
    for t in turns:
        result = app.invoke({"messages": [HumanMessage(content=t)], "user_query": t}, config=config)
    return result, result["messages"][-1].content


def body(text):
    return text.split("## Checks")[0]


def day_section(text):
    return text.split("## Day-by-day")[-1].split("## Where to stay")[0]


def no_entry_docs(text):
    return planning.ENTRY_DOCS_RE.search(body(text)) is None


def only_api_flights(result, text):
    api = {f["flight"] for f in result.get("flights", [])}
    shown = {f"{m.group(1)}{m.group(2)}" for m in planning.FLIGHT_NO_RE.finditer(body(text))}
    return shown <= api


def budget_ok(result):
    return result.get("budget") is not None and planning.check_budget_math(result["budget"])


CASES = [
    ("'trip kochi to goa' asks first; no passport",
     ("trip kochi to goa",),
     lambda r, t: "how many days" in t.lower() and no_entry_docs(t)),
    ("Clarify → answer → domestic plan, no passport/visa",
     ("trip kochi to goa", "4 days, 2 people, budget 40000"),
     lambda r, t: "## Day-by-day" in t and no_entry_docs(t)),
    ("Domestic, no hand-written KB (Hampi): plan + no visa",
     ("plan 3 days from mumbai to hampi for 2 people, budget 30000",),
     lambda r, t: "## Day-by-day" in t and no_entry_docs(t) and budget_ok(r)),
    ("International (Paris): flights only from API, budget adds up",
     ("plan 5 days from delhi to paris for 2 people, budget 3 lakh",),
     lambda r, t: only_api_flights(r, t) and budget_ok(r)),
    ("International (Tokyo): plan works",
     ("plan 3 days from chennai to tokyo for 1 person, budget 2 lakh",),
     lambda r, t: "## Day-by-day" in t and budget_ok(r)),
    ("Budget total equals sum of items (Goa, 3 people)",
     ("plan 5 days from mumbai to goa for 3 people under 1 lakh",),
     lambda r, t: budget_ok(r) and "Total (whole group)" in t),
    ("No impossible nearby trips (Diu from Goa)",
     ("plan 3 days from kochi to goa for 1 person, budget 25000, include a day trip to diu",),
     lambda r, t: "diu" not in day_section(t).lower()),
    ("'hi' is chat, no plan",
     ("hi",),
     lambda r, t: "## Day-by-day" not in t),
]


if __name__ == "__main__":
    print(f"Mode: {'LIVE APIs' if LIVE else 'MOCK (offline)'}\n")
    failed = 0
    for name, turns, check in CASES:
        try:
            result, text = run(*turns)
            ok = check(result, text)
        except Exception as e:
            ok, text = False, f"ERROR: {e!r}"
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("      " + re.sub(r"\s+", " ", text)[:400])
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)
