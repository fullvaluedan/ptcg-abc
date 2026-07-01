"""Deck harvest tests.

Decklist extraction, aggregation, and ranking are exercised on synthetic replays
shaped like the real episode JSON (a 60 card action list at the deck-selection
step, info.TeamNames, and a rewards pair). Directory and streamed .zip sources
are both covered, and card name loading runs against a tiny temp CSV so the
suite stays fully offline.
"""
import json
import zipfile

import pytest

from tools import deck_harvest


def _deck(first):
    """A 60 card deck starting with a distinguishing id, padded with energy."""
    return [first] + [1] * 59


def _replay(teams, rewards, decks, deck_step=1):
    """Build a replay: an empty handshake step then a deck-selection step.

    decks is a per seat 60 card list placed as that seat's action at deck_step.
    """
    steps = [[{"action": []}, {"action": []}]]
    while len(steps) <= deck_step:
        steps.append([{"action": []}, {"action": []}])
    for seat, deck in enumerate(decks):
        steps[deck_step][seat] = {"action": list(deck)}
    return {
        "info": {"TeamNames": list(teams)},
        "rewards": list(rewards),
        "steps": steps,
    }


def test_extract_seat_decks_marks_winner_and_deck():
    rep = _replay(["Alice", "Bob"], [1, -1], [_deck(721), _deck(164)])
    recs = deck_harvest.extract_seat_decks(rep)
    assert len(recs) == 2
    alice = next(r for r in recs if r["team"] == "Alice")
    bob = next(r for r in recs if r["team"] == "Bob")
    assert alice["won"] is True
    assert bob["won"] is False
    assert alice["deck"][0] == 721
    assert len(alice["deck"]) == 60


def test_extract_seat_decks_draw_wins_for_neither():
    rep = _replay(["Alice", "Bob"], [0, 0], [_deck(721), _deck(164)])
    recs = deck_harvest.extract_seat_decks(rep)
    assert all(r["won"] is False for r in recs)


def test_extract_seat_decks_malformed_returns_empty():
    assert deck_harvest.extract_seat_decks({}) == []
    assert deck_harvest.extract_seat_decks({"steps": []}) == []
    # A short action is an in game move, not a decklist.
    short = {"info": {"TeamNames": ["A", "B"]}, "rewards": [1, -1],
             "steps": [[{"action": [3, 3, 3]}, {"action": [4]}]]}
    assert deck_harvest.extract_seat_decks(short) == []


def test_deck_signature_is_order_independent():
    assert deck_harvest.deck_signature([3, 1, 2]) == deck_harvest.deck_signature([2, 3, 1])
    assert deck_harvest.deck_signature([1, 1, 2]) != deck_harvest.deck_signature([1, 2, 2])


def test_harvest_directory_aggregates_wins(tmp_path):
    # Alice's deck wins twice, Bob's deck loses twice, over two episodes.
    for i, rewards in enumerate([[1, -1], [1, -1]]):
        rep = _replay(["Alice", "Bob"], rewards, [_deck(721), _deck(164)])
        (tmp_path / f"ep{i}.json").write_text(json.dumps(rep), encoding="utf-8")
    agg = deck_harvest.harvest(tmp_path)
    assert agg["episodes"] == 2
    assert agg["records"] == 4
    ranked = deck_harvest.rank_decks(agg, min_games=1)
    top_sig, top_entry, top_wr = ranked[0]
    assert top_entry["deck"][0] == 721
    assert top_entry["wins"] == 2
    assert top_entry["games"] == 2
    assert top_wr == pytest.approx(1.0)
    assert top_entry["teams"] == {"Alice"}


def test_harvest_team_filter_restricts_seats(tmp_path):
    rep = _replay(["Alice", "Bob"], [1, -1], [_deck(721), _deck(164)])
    (tmp_path / "ep.json").write_text(json.dumps(rep), encoding="utf-8")
    agg = deck_harvest.harvest(tmp_path, teams=["alice"])
    assert agg["records"] == 1
    assert len(agg["by_sig"]) == 1
    entry = next(iter(agg["by_sig"].values()))
    assert entry["teams"] == {"Alice"}


def test_harvest_limit_caps_episodes(tmp_path):
    for i in range(5):
        rep = _replay(["Alice", "Bob"], [1, -1], [_deck(721), _deck(164)])
        (tmp_path / f"ep{i}.json").write_text(json.dumps(rep), encoding="utf-8")
    agg = deck_harvest.harvest(tmp_path, limit=2)
    assert agg["episodes"] == 2


def test_iter_replays_streams_zip(tmp_path):
    rep = _replay(["Alice", "Bob"], [1, -1], [_deck(721), _deck(164)])
    zpath = tmp_path / "day.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("111.json", json.dumps(rep))
        zf.writestr("notes.txt", "ignore me")
        zf.writestr("bad.json", "{not json")
    seen = list(deck_harvest.iter_replays(zpath))
    assert len(seen) == 1  # txt skipped, corrupt json skipped
    assert seen[0][0] == "111.json"
    agg = deck_harvest.harvest(zpath)
    assert agg["records"] == 2


def test_load_card_names_and_fingerprint(tmp_path):
    csv_path = tmp_path / "cards.csv"
    csv_path.write_text(
        "Card ID,Card Name,Category\n"
        "721,Kyogre,n/a\n"
        "1,Basic {G} Energy,n/a\n",
        encoding="utf-8",
    )
    names = deck_harvest.load_card_names(csv_path)
    assert names[721][0] == "Kyogre"
    fp = deck_harvest.deck_fingerprint(_deck(721), names)
    # 59 energy first (highest count), then the single Kyogre.
    assert fp[0] == (59, 1, "Basic {G} Energy")
    assert fp[1] == (1, 721, "Kyogre")


def test_load_card_names_missing_file_returns_empty(tmp_path):
    assert deck_harvest.load_card_names(tmp_path / "nope.csv") == {}


def test_write_deck_roundtrip(tmp_path):
    deck = _deck(721)
    out = tmp_path / "decks" / "harvested.csv"
    deck_harvest.write_deck(deck, out)
    lines = [int(x) for x in out.read_text().split("\n") if x.strip()]
    assert lines == deck
