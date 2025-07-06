import pytest
from game.card.ydke import Deck
from game.edo import banlists

SINGLE_BANLIST_PATH = "tests/data/banlists/0TCG.lflist.conf"
BANLIST_FOLDER = "tests/data/banlists"
TCG_BANLIST_HASH = 3297508800

# make a function to reset the banlist manager
@pytest.fixture(autouse=True)
def reset_banlist_manager():
    manager = banlists.BanlistManager()
    manager.banlists = []
    manager.banlists_path = None
    manager._initialized = False

def test_load_banlist(reset_banlist_manager):
    manager = banlists.BanlistManager(load_banlists=False)
    manager.load_banlist(SINGLE_BANLIST_PATH)
    assert len(manager.banlists) == 1
    assert manager.banlists[0].name == "2024.12 TCG"
    assert not manager.banlists[0].whitelist
    assert len(manager.banlists[0].content) > 0
    assert manager.banlists[0].content[43262273] == 0
    assert manager.banlists[0].content[92107604] == 2
    assert manager.banlists[0].hash == TCG_BANLIST_HASH

def test_load_all_banlists():
    # this should basically also add the no limits banlist which is in memory
    manager = banlists.BanlistManager(BANLIST_FOLDER, load_banlists=False)
    manager.load_all_banlists()
    assert len(manager.banlists) == 2
    assert manager.banlists[0].name == "2024.12 TCG"
    assert manager.banlists[1].name == "No limits"
    assert not manager.banlists[0].whitelist
    assert not manager.banlists[1].whitelist
    assert len(manager.banlists[0].content) > 0
    assert len(manager.banlists[1].content) == 0
    assert manager.banlists[1].content == {}

def test_get_limit_success():
    manager = banlists.BanlistManager(BANLIST_FOLDER)
    manager.load_all_banlists()
    assert manager.banlists[0].get_limit(43262273) == 0

def test_banlist_is_deck_allowed_success():
    manager = banlists.BanlistManager(BANLIST_FOLDER)
    manager.load_all_banlists()
    cards = [123456789]
    deck = Deck(cards, cards, "json")
    assert manager.banlists[1].is_deck_allowed(deck) == (True, {})


def test_banlist_is_deck_allowed_fail():
    manager = banlists.BanlistManager(BANLIST_FOLDER)
    manager.load_all_banlists()
    cards = [43262273, 43262273, 43262273]
    deck = Deck(cards, cards, "json")
    result, reason = manager.banlists[0].is_deck_allowed(deck)
    assert not result
    print(reason)
    assert 43262273 in reason.keys()
    assert reason[43262273].limit == 0
    assert reason[43262273].found == 6 # main + side

def test_is_deck_allowed_with_limited_cards():
    manager = banlists.BanlistManager(BANLIST_FOLDER)
    manager.load_all_banlists()
    cards = [34124316, 34124316] # 2 is the limit
    deck = Deck(cards, [], "json")
    result, reason = manager.banlists[0].is_deck_allowed(deck)
    assert result
    assert reason == {}
    cards = [34124316, 34124316, 34124316] # 2 is the limit
    deck = Deck(cards, [], "json")
    result, reason = manager.banlists[0].is_deck_allowed(deck)
    assert not result
    assert 34124316 in reason.keys()
    assert reason[34124316].limit == 2
    assert reason[34124316].found == 3 # main
