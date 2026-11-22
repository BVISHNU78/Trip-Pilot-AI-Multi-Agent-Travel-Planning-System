"""Whole graph end-to-end in mock mode - the evaluation set, offline."""
import uuid

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

import planning
from main import graph

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


def shown_flights(text):
    return {f"{m.group(1)}{m.group(2)}" for m in planning.FLIGHT_NO_RE.finditer(body(text))}


def test_hi_is_chat():
    _, text = run("hi")
    assert "## Day-by-day" not in text


def test_vague_request_asks_first():
    _, text = run("trip kochi to goa")
    assert "how many days" in text.lower()
    assert planning.ENTRY_DOCS_RE.search(text) is None


def test_clarify_then_answer_gives_plan():
    _, text = run("trip kochi to goa", "4 days, 2 people, budget 40000")
    assert "## Day-by-day" in text
    assert text.count("### Day ") == 4


def test_assume_states_assumptions():
    _, text = run("trip kochi to goa", "assume")
    assert "## Assumptions" in text and "assumed" in text


@pytest.mark.parametrize("request_text, domestic", [
    ("plan 3 days from kochi to goa for 2 people, budget 40000", True),
    ("plan 4 days from mumbai to hampi for 2 people, budget 30000", True),
    ("plan 5 days from delhi to paris for 2 people, budget 3 lakh", False),
    ("plan 3 days from chennai to tokyo for 1 person, budget 2 lakh", False),
    ("plan 3 days from kochi to reykjavik for 2 people, budget 4 lakh", None),   # country unknown to mock
])
def test_any_destination_full_plan(request_text, domestic):
    result, text = run(request_text)
    assert "## Day-by-day" in text
    # Budget always adds up
    assert planning.check_budget_math(result["budget"])
    assert "Total (whole group)" in text
    # Flights: only what the API returned
    assert shown_flights(text) <= {f["flight"] for f in result["flights"]}
    # Every listed place comes from the knowledge base, and any without a source is flagged
    for d in result["plan"]["days"]:
        for a in d["activities"]:
            assert a["verified"]
            if not a["source"]:
                assert any(a["name"] in w and "No source" in w for w in result["warnings"])
    # Domestic → no passport/visa; international → generic note only
    if domestic:
        assert planning.ENTRY_DOCS_RE.search(body(text)) is None
    if domestic is False:
        assert "visa requirements" in text


def test_no_impossible_nearby_trip():
    result, text = run("plan 3 days from kochi to goa for 1 person, budget 25000, include a day trip to diu")
    assert "diu" not in day_section(text).lower()


def test_unknown_place_never_reaches_itinerary():
    _, text = run("plan 3 days from delhi to paris for 2 people, budget 3 lakh")
    days = day_section(text)
    assert "Imaginary Crystal Palace" not in days
    assert "Distant Island" not in days


def test_mock_banner_shown():
    _, text = run("plan 2 days from kochi to goa for 1 person, budget 20000")
    assert "MOCK MODE" in text
