"""Auto-built knowledge base for destinations without a hand-written file (mock mode)."""
from knowledge.builder import get_kb, mentioned
from knowledge import distance_km
import providers


def test_mock_mode_is_on():
    assert providers.mock_mode()


def test_local_kb_used_for_goa():
    kb, _ = get_kb("Goa", "India")
    assert kb["name"] == "Goa" and not kb.get("auto_built")


def test_any_destination_gets_a_kb():
    for dest in ["Paris", "Hampi", "Reykjavik", "Some Unknown Town"]:
        kb, notes = get_kb(dest)
        assert kb and kb["auto_built"], dest
        assert len(kb["places"]) >= 3
        assert all(p["source"] for p in kb["places"])


def test_invented_place_is_rejected():
    kb, notes = get_kb("Paris", "France")
    names = [p["name"] for p in kb["places"]]
    assert "Imaginary Crystal Palace" not in names
    assert any("Imaginary Crystal Palace" in n and "not named" in n for n in notes)


def test_far_away_place_is_rejected():
    kb, notes = get_kb("Paris", "France")
    assert not any("Distant Island" in p["name"] for p in kb["places"])
    assert any("Distant Island" in n and "too far" in n for n in notes)
    assert all(distance_km(kb, "center", p) <= 80 for p in kb["places"])


def test_mentioned_matching():
    assert mentioned("Eiffel Tower", "Visit the Eiffel Tower at night")
    assert mentioned("Musée du Louvre", "the Louvre musée is huge")
    assert not mentioned("Imaginary Crystal Palace", "Eiffel Tower and Louvre")
