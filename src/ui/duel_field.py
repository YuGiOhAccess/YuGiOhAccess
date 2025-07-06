import logging

from enum import unique, StrEnum
import struct

import wx

from ui.base_ui import BaseUI
from ui import action_menu
from ui import duel_menu

from ui import card_list_ui
from ui import tab_order

from core import dotdict, utils
from core import variables

from game.card import card_constants
from game.card.card import Card
from game.card.location_conversion import LocationConversion
from game.edo import structs

logger = logging.getLogger(__name__)

# we need a zone class, that holds a machine generated label
# the card clas, and the edopro location
class Zone:
    def __init__(self, label, card):
        self.label = label
        self.card = card
        self._controller = -1
        self._location = -1
        self._sequence = -1
        self._position = -1

    @property
    def controller(self):
        # if the controller is -1, we have not set it yet
        if isinstance(self.card, Card):
            return self.card.controller
        return self._controller
    
    @controller.setter
    def controller(self, value):
        self._controller = value

    @property
    def location(self):
        if isinstance(self.card, Card):
            return self.card.location
        return self._location
    
    @location.setter
    def location(self, value):
        self._location = value

    @property
    def sequence(self):
        if isinstance(self.card, Card):
            return self.card.sequence
        return self._sequence
    
    @sequence.setter
    def sequence(self, value):
        self._sequence = value

    @property
    def position(self):
        if isinstance(self.card, Card):
            return self.card.position
        return self._position
    
    @position.setter
    def position(self, value):
        self._position = value

    def __str__(self):
        return self.label
    
    def __eq__(self, other):
        return self.label == other.label

# we need keys for all the zones, where there's more than 1 card
# match them to the rows below, in the format "row{}", where the backet will be filled in later
@unique
class ZONE_KEYS(StrEnum):
    OPPONENT_HAND = "oh{}"
    OPPONENT_SPELL_AND_TRAP = "os{}"
    OPPONENT_MONSTER = "om{}"
    EXTRA_MONSTER = "q{}"
    PLAYER_MONSTER = "pm{}"
    PLAYER_SPELL_AND_TRAP = "ps{}"
    PLAYER_HAND = "ph{}"
    EXTRA_INFORMATION = "ei{}"
    OPPONENT_EXTRA_DECK = "ox{}"
    PLAYER_EXTRA_DECK = "px{}"
    # the following only has 1 zone, so they do not have a formatable string
    PLAYER_SPELL_FIELD = "pf"
    OPPONENT_SPELL_FIELD = "opf"
    OPPONENT_GRAVEYARD = "og{}"
    PLAYER_GRAVEYARD = "pg{}"
    OPPONENT_BANISHED = "or{}"
    PLAYER_BANISHED = "pr{}"
    OPPONENT_DECK = "od"
    PLAYER_DECK = "pd"
    

class DuelField(BaseUI):
    def __init__(self, client):
        super(DuelField, self).__init__(8, 60, "Duel Field", allow_movement_to_none=False)
        self.set_help_text("Arrow keys to navigate field. Enter on a card to open action menu. Space to read a card. Backspace to open duel menu. Escape to cancel chaining.")
        center_x = int(self.center_x)
        center_y = int(self.center_y)
        self.client = client
        self.set_position(center_y, center_x)
        self.opponent_hand_row = 0
        self.opponent_spell_and_trap_row = 1
        self.opponent_monster_row = 2
        self.extra_monster_row = 3
        self.player_monster_row = 4
        self.player_spell_and_trap_row = 5
        self.player_hand_row = 6
        self.extra_information_row = 7

        self.zones = {}
        self.tab_order = tab_order.DuelFieldTabOrder()

        # setup the field
        self.amount_of_zones = 4 # 0, 1, 2, 3 and 4
        self.setup_field()

        self._preemtive_key_handler = None

        # bind event handlers
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def __str__(self):
        result = "DuelField\n"
        line_counter = 0
        for zone_keys in self.zones.keys():
            result += f"{zone_keys}: {self.zones[zone_keys]}"
            line_counter += 1
            if line_counter == 3:
                result += "\n"
                line_counter = 0
        return result

    @property
    def preemtive_key_handler(self):
        return self._preemtive_key_handler
    
    @preemtive_key_handler.setter
    def preemtive_key_handler(self, value):
        if not value:
            logger.debug("Setting preemtive key handler to None.")
            self._preemtive_key_handler = None
            return
        logger.debug(f"Setting preemtive key handler to {value}.")
        self._preemtive_key_handler = value

    def set_cell(self, row, col, value, function=None, *args, **kwargs):
        self.cells[row][col] = value
        self.cell_functions[row][col] = function

    def get_subset_of_zones(self, start):
        """Return a dictionary of zones. Include all zones whos keys starts with the start parameter"""
        return {k: v for k, v in self.zones.items() if k.startswith(start)}

    def get_zone_from_current_position(self, subset=None):
        if not subset:
            subset = self.zones
        for zone in subset.values():
            if zone.label == self.get_cell(self.current_row, self.current_col):
                return zone
        return None
    
    def get_card_information_to_show_when_card_is_selected(self, zone):
        # if the zones card attribute is not a card, it's a string
        if not isinstance(zone.card, Card):
            return str(zone.card)
        if zone.card.code == 0:
            return "Face down card"
        text_to_show = self.resolve_labels_for_card(zone.card)
        # lastly add the card name
        text_to_show += zone.card.get_name()
        if zone.card.type & card_constants.TYPE.MONSTER:
            text_to_show += f" ({zone.card.attack}/{zone.card.defense})"
        if zone.location & card_constants.LOCATION.ONFIELD:
            # add the position of the card
            text_to_show += card_constants.POSITION(zone.position).name
        return text_to_show
        
    def resolve_labels_for_card(self, card):
        text_to_show = ""
        if card in self.client.player.activatable:
            text_to_show += "Has activatable effects, "
        print(f"{card} in {self.client.player.chaining_cards}")
        if card in self.client.player.chaining_cards:
            text_to_show += "Chaining, "
        if card in self.client.player.attackable:
            text_to_show += "Can attack, "
        # test for summonables
        if card in self.client.player.summonable:
            text_to_show += "Summonable, "
        if card in self.client.player.special_summonable:
            text_to_show += "Special summonable, "
        if card in self.client.player.repositionable:
            text_to_show += "Repositionable, "
        if card in self.client.player.monster_settable or card in self.client.player.spell_settable:
            text_to_show += "settable, "
        return text_to_show
 
    def resolve_chain(self, zone):
        if not zone:
            return False
        if isinstance(zone, str):
            return False
        if not zone.card:
            utils.output("No card selected")
            return False
        card = zone.card
        # if card is not instance of card, it's a string
        if not isinstance(card, Card):
            return False
        # see if we can find the card in the chain cards
        for chain_card in self.client.player.chaining_cards:
            print(f"Selected card {card.name}, current chain card: {chain_card.name}")
            if chain_card == card:
                self.tab_order.set_tabable_items([])
                logger.debug(f"Chaining card: {chain_card.name}, with chain index {chain_card.chain_index}")
                self.client.send(structs.ClientIdType.RESPONSE, struct.pack('I', chain_card.chain_index))
                self.preemtive_key_handler = None
            return True
        return False

    def on_cell_change(self,  old_row, old_col, new_row, new_col, cell):
        zone = self.get_zone_from_current_position()
        if isinstance(zone, Zone):
            info = self.get_card_information_to_show_when_card_is_selected(zone)
            utils.output(info)
        else:
            cell = self.get_cell(new_row, new_col)
            if not cell:
                utils.output("")
            else:
                utils.output(str(cell))

    def setup_field(self):
        # set up 5 zones for the player and 5 zones for the opponent
        for i in range(self.amount_of_zones+1):
            self.set_opponent_spell_and_trap_zone(i, f"Empty opponent Spell/Trap {i+1}")
            self.set_opponent_monster_zone(i, f"Empty opponent Monster {i+1}")
            self.set_player_spell_and_trap_zone(i, f"Empty Spell/Trap {i+1}")
            self.set_player_monster_zone(i, f"Empty Monster {i+1}")
        # the following are there only 1 or 2 of, so set them, manually
        self.set_extra_monster_zone(0, "Empty extra Monster 1")
        self.set_extra_monster_zone(1, "Empty extra Monster 2")
        self.set_player_field_spell("Empty Field Spell")
        self.set_opponent_field_spell("Empty opponent Field Spell")
        self.set_opponent_deck_zone("Opponent Deck")
        self.set_player_deck_zone("Player Deck")
        self.set_opponent_extra_deck_zone(0, "Opponent Extra Deck")
        self.set_opponent_graveyard_zone(0, "Opponent Graveyard")
        self.set_player_graveyard_zone(0, "Player Graveyard")
        self.set_opponent_banished_zone(0, "Opponent Banished")
        self.set_player_banished_zone(0, "Player Banished")
        if variables.config.get("helper_zones"):
            self.create_helper_zones()

    def update_field(self, client, controller, location, queries):
        print("Updating field")
        _player = "You" if controller == client.what_player_am_i else "Your opponent"
        location_enum = card_constants.LOCATION(location)
        if location_enum == card_constants.LOCATION.HAND:
            if controller == client.what_player_am_i:
                self.handle_player_hand(queries)
            else:
                self.handle_opponent_hand(queries)
        elif location_enum == card_constants.LOCATION.EXTRA:
            if controller == client.what_player_am_i:
                self.handle_player_extra_deck(queries)
            else:
                print("Handling opponent extra deck")
                self.handle_opponent_extra_deck(queries)
        elif location_enum == card_constants.LOCATION.MONSTER_ZONE:
            if controller == client.what_player_am_i:
                self.handle_player_monster_zone(queries)
            else:
                self.handle_opponent_monster_zone(queries)
        elif location_enum == card_constants.LOCATION.SPELL_AND_TRAP_ZONE:
            if controller == client.what_player_am_i:
                self.handle_player_spell_and_trap_zone(queries)
            else:
                self.handle_opponent_spell_and_trap_zone(queries)
        else:
            logger.warning(f"Unhandled location: {location_enum.name}")
            print(f"Player: {_player}\nQueries:\n{queries}")
    

    def handle_player_hand(self, queries):
        # first clear our hand
        self.clear_player_hand()
        for query in queries:
            if query.onfield_skipped:
                continue
            # create a card object
            card = Card(query.code)
            card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            # append it to our hand
            self.append_card_to_player_hand(card)

    def handle_opponent_hand(self, queries):
        # first clear our hand
        self.clear_opponent_hand()
        for query in queries:
            if query.onfield_skipped:
                continue
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            self.append_card_to_opponent_hand(card, query)

    def handle_player_extra_deck(self, queries):
        # clear the extra deck
        for zone_key in self.get_subset_of_zones("px").keys():
            del self.zones[zone_key]
        for query in queries:
            if query.onfield_skipped:
                continue
            card = Card(query.code)
            card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            self.append_card_to_player_extra_deck(card)

    def handle_opponent_extra_deck(self, queries):
        # clear the extra deck
        for zone_key in self.get_subset_of_zones("ox").keys():
            del self.zones[zone_key]
        for query in queries:
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            self.append_card_to_opponent_extra_deck(card, query)

    def handle_player_monster_zone(self, queries):
        for i, query in enumerate(queries):
            if query.onfield_skipped:
                continue
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            if query.sequence == 5:
                self.set_extra_monster_zone(0, card)
            elif query.sequence == 6:
                self.set_extra_monster_zone(1, card)
            else:
                self.set_player_monster_zone(query.sequence, card)

    def handle_opponent_monster_zone(self, queries):
        for i, query in enumerate(queries):
            if query.onfield_skipped:
                continue
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            if query.sequence == 5: # keep in mind it's reversed
                self.set_extra_monster_zone(1, card)
            elif query.sequence == 6:
                self.set_extra_monster_zone(0, card)
            else:
                self.set_opponent_monster_zone(query.sequence, card)

    def handle_player_spell_and_trap_zone(self, queries):
        for i, query in enumerate(queries):
            if query.onfield_skipped:
                continue
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            if query.sequence == 5:
                self.set_player_field_spell(card)
            else:
                self.set_player_spell_and_trap_zone(query.sequence, card)

    def handle_opponent_spell_and_trap_zone(self, queries):
        for i, query in enumerate(queries):
            if query.onfield_skipped:
                continue
            if hasattr(query, "code"):
                card = Card(query.code)
                card.set_location_and_position_info(query.controller, query.location, query.sequence, query.position)
            else:
                card = "Face down card"
            if query.sequence == 5:
                self.set_opponent_field_spell(card)
            else:
                self.set_opponent_spell_and_trap_zone(query.sequence, card)

    def append_card_to_player_hand(self, new_card):
        # clear the row
        for x in range(self.cols):
            self.cells[self.player_hand_row][x] = None
        player_hand = self.get_subset_of_zones("ph")
        new_zone = Zone(ZONE_KEYS.PLAYER_HAND.format(len(player_hand)), new_card)
        self.zones[new_zone.label] = new_zone
        player_hand = self.get_subset_of_zones("ph")
        # set the cards back, keepingi n mind that we want to center it.
        # so it becomes center/2 - len(cards)/2
        for i, zone in enumerate(player_hand):
            col = int(round((self.center_x - len(player_hand)/2),0)) + i
            self.set_cell(self.player_hand_row, col, str(zone))

    def append_card_to_opponent_hand(self, new_card, query):
        for x in range(self.cols):
            self.cells[self.opponent_hand_row][x] = None
        opponent_hand = self.get_subset_of_zones("oh")
        new_zone = Zone(ZONE_KEYS.OPPONENT_HAND.format(len(opponent_hand)), new_card)
        new_zone.controller = query.controller
        new_zone.location = query.location
        new_zone.sequence = query.sequence
        new_zone.position = query.position
        self.zones[new_zone.label] = new_zone
        opponent_hand = self.get_subset_of_zones("oh")
        for i, zone in enumerate(opponent_hand):
            col = int(round((self.center_x - len(opponent_hand)/2),0)) + i
            self.set_cell(self.opponent_hand_row, col, str(zone))

    def append_card_to_player_extra_deck(self, new_card):
        player_extra_deck = self.get_subset_of_zones("px")
        new_zone = Zone(ZONE_KEYS.PLAYER_EXTRA_DECK.format(len(player_extra_deck)), new_card)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.player_spell_and_trap_row, int(self.center_x-3), f"Extra deck {len(player_extra_deck)+1}")

    def append_card_to_opponent_extra_deck(self, new_card, query):
        opponent_extra_deck = self.get_subset_of_zones("ox")
        new_zone = Zone(ZONE_KEYS.OPPONENT_EXTRA_DECK.format(len(opponent_extra_deck)), new_card)
        new_zone.controller = query.controller
        new_zone.location = query.location
        new_zone.sequence = query.sequence
        new_zone.position = query.position
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.opponent_spell_and_trap_row, int(self.center_x+3), f"Extra deck {len(opponent_extra_deck)+1}")

    def append_card_to_player_graveyard(self, new_card):
        player_graveyard = self.get_subset_of_zones("pg")
        new_zone = Zone(ZONE_KEYS.PLAYER_GRAVEYARD.format(len(player_graveyard)), new_card)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.player_monster_row, int(self.center_x+3), f"player graveyard {len(player_graveyard)+1}")

    def append_card_to_opponent_graveyard(self, new_card, query):
        opponent_graveyard = self.get_subset_of_zones("og")
        new_zone = Zone(ZONE_KEYS.OPPONENT_GRAVEYARD.format(len(opponent_graveyard)), new_card)
        new_zone.controller = query.controller
        new_zone.location = query.location
        new_zone.sequence = query.sequence
        new_zone.position = query.position
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.opponent_monster_row, int(self.center_x-3), f"opponent graveyard {len(opponent_graveyard)+1}")

    def append_card_to_player_banished(self, new_card):
        player_banished = self.get_subset_of_zones("pr")
        new_zone = Zone(ZONE_KEYS.PLAYER_BANISHED.format(len(player_banished)), new_card)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.player_monster_row, int(self.center_x+4), f"player banished {len(player_banished)+1}")

    def append_card_to_opponent_banished(self, new_card, query):
        opponent_banished = self.get_subset_of_zones("or")
        new_zone = Zone(ZONE_KEYS.OPPONENT_BANISHED.format(len(opponent_banished)), new_card)
        new_zone.controller = query.controller
        new_zone.location = query.location
        new_zone.sequence = query.sequence
        new_zone.position = query.position
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.opponent_monster_row, int(self.center_x-4), f"opponent banished {len(opponent_banished)+1}")

    def clear_player_hand(self):
        # delete all keys that start with the player hand row
        for key in self.get_subset_of_zones("ph"):
            del self.zones[key]
        for x in range(self.cols):
            self.cells[self.player_hand_row][x] = None

    def clear_opponent_hand(self):
        # delete all keys that start with the opponent hand row
        for key in self.get_subset_of_zones("oh"):
            del self.zones[key]
        for x in range(self.cols):
            self.cells[self.opponent_hand_row][x] = None

    def clear_player_extra_deck(self):
        for key in self.get_subset_of_zones("px"):
            del self.zones[key]
        self.set_cell(self.player_spell_and_trap_row, int(self.center_x-3), "Empty player extra deck")

    def clear_opponent_extra_deck(self):
        for key in self.get_subset_of_zones("ox"):
            del self.zones[key]
        self.set_cell(self.opponent_spell_and_trap_row, int(self.center_x+3), "Empty opponent extra deck")

    def clear_player_graveyard(self):
        for key in self.get_subset_of_zones("pg"):
            del self.zones[key]
        self.set_cell(self.player_monster_row, int(self.center_x+3), "Empty player graveyard")

    def clear_opponent_graveyard(self):
        for key in self.get_subset_of_zones("og"):
            del self.zones[key]
        self.set_cell(self.opponent_monster_row, int(self.center_x-3), "Empty opponent graveyard")

    def clear_player_banished(self):
        for key in self.get_subset_of_zones("pr"):
            del self.zones[key]
        self.set_cell(self.player_monster_row, int(self.center_x+4), "Empty player banished")

    def clear_opponent_banished(self):
        for key in self.get_subset_of_zones("or"):
            del self.zones[key]
        self.set_cell(self.opponent_monster_row, int(self.center_x-4), "Empty opponent banished")

    def remove_card(self, card):
        # if location is hand, get all the zones in the hand and readd them
        if card.location == card_constants.LOCATION.HAND:
            if card.controller == self.client.what_player_am_i:
                cards_in_hand = self.get_subset_of_zones("ph")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del cards_in_hand[zone_key]
                self.clear_player_hand()
                for i, zone in enumerate(cards_in_hand.values()):
                    self.append_card_to_player_hand(zone.card)
            else:
                cards_in_hand = self.get_subset_of_zones("oh")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del cards_in_hand[zone_key]
                self.clear_opponent_hand()
                for i, zone in enumerate(   cards_in_hand.values()):
                    fake_query = dotdict.DotDict()
                    fake_query.controller = zone.controller
                    fake_query.location = zone.location
                    fake_query.sequence = zone.sequence
                    fake_query.position = zone.position
                    self.append_card_to_opponent_hand(zone.card, fake_query)
        if card.location == card_constants.LOCATION.EXTRA:
            if card.controller == self.client.what_player_am_i:
                extra_deck = self.get_subset_of_zones("px")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del extra_deck[zone_key]
                self.clear_player_extra_deck()
                for i, zone in enumerate(extra_deck.values()):
                    self.append_card_to_player_extra_deck(zone.card)
            else:
                extra_deck = self.get_subset_of_zones("ox")
                if len(extra_deck) <= 1:
                    return
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del extra_deck[zone_key]
                self.clear_opponent_extra_deck()
                for i, zone in enumerate(extra_deck.values()):
                    fake_query = dotdict.DotDict()
                    fake_query.controller = zone.controller
                    fake_query.location = zone.location
                    fake_query.sequence = zone.sequence
                    fake_query.position = zone.position
                    self.append_card_to_opponent_extra_deck(zone.card, fake_query)
        if card.location == card_constants.LOCATION.GRAVE:
            if card.controller == self.client.what_player_am_i:
                graveyard = self.get_subset_of_zones("pg")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del graveyard[zone_key]
                self.clear_player_graveyard()
                for i, zone in enumerate(graveyard.values()):
                    self.append_card_to_player_graveyard(zone.card)
            else:
                graveyard = self.get_subset_of_zones("og")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del graveyard[zone_key]
                self.clear_opponent_graveyard()
                for i, zone in enumerate(graveyard.values()):
                    fake_query = dotdict.DotDict()
                    fake_query.controller = zone.controller
                    fake_query.location = zone.location
                    fake_query.sequence = zone.sequence
                    fake_query.position = zone.position
                    self.append_card_to_opponent_graveyard(zone.card, fake_query)
        if card.location == card_constants.LOCATION.REMOVED:
            if card.controller == self.client.what_player_am_i:
                banished = self.get_subset_of_zones("pr")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del banished[zone_key]
                self.clear_player_banished()
                for i, zone in enumerate(banished.values()):
                    self.append_card_to_player_banished(zone.card)
            else:
                banished = self.get_subset_of_zones("or")
                zone_key = LocationConversion.from_card_location(self.client, card).to_zone_key()
                del banished[zone_key]
                self.clear_opponent_banished()
                for i, zone in enumerate(banished.values()):
                    fake_query = dotdict.DotDict()
                    fake_query.controller = zone.controller
                    fake_query.location = zone.location
                    fake_query.sequence = zone.sequence
                    fake_query.position = zone.position
                    self.append_card_to_opponent_banished(zone.card, fake_query)
        location_information = LocationConversion.from_card_location(self.client, card)
        if card.location == card_constants.LOCATION.MONSTER_ZONE:
            if card.controller == self.client.what_player_am_i:
                if card.sequence > 4:
                    self.set_extra_monster_zone(location_information.sequence-5, f"Empty extra Monster {location_information.sequence-4}")
                else:
                    self.set_player_monster_zone(location_information.sequence, f"Empty Monster {location_information.sequence+1}")
            else:
                if card.sequence > 4:
                    self.set_extra_monster_zone(location_information.sequence-5, f"Empty extra Monster {location_information.sequence-4}")
                else:
                    self.set_opponent_monster_zone(location_information.sequence, f"Empty Monster {location_information.sequence+1}")
        if card.location == card_constants.LOCATION.SPELL_AND_TRAP_ZONE:
            if card.controller == self.client.what_player_am_i:
                self.set_player_spell_and_trap_zone(location_information.sequence, f"Empty Spell/Trap {location_information.sequence+1}")
            else:
                self.set_opponent_spell_and_trap_zone(location_information.sequence, f"Empty Spell/Trap {location_information.sequence+1}")
        if card.location == card_constants.LOCATION.FIELD_ZONE:
            if card.controller == self.client.what_player_am_i:
                self.set_player_field_spell("Empty Field Spell")
            else:
                self.set_opponent_field_spell("Empty Opponent Field Spell")


            
    def set_opponent_spell_and_trap_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.OPPONENT_SPELL_AND_TRAP.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        # so it starts from (amount_of_zones/2) + center_x and goes left
        # get the right zone
        right_most_zone = int(self.center_x + (self.amount_of_zones/2))
        zone_to_update = right_most_zone - zone
        # set the card
        self.set_cell(self.opponent_spell_and_trap_row, zone_to_update, str(new_zone))
        
    def set_opponent_monster_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.OPPONENT_MONSTER.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        # so it starts from (amount_of_zones/2) + center_x and goes left
        # get the right zone
        right_most_zone = int(self.center_x + (self.amount_of_zones/2))
        zone_to_update = right_most_zone - zone
        # set the card
        self.set_cell(self.opponent_monster_row, zone_to_update, str(new_zone))

    def set_player_spell_and_trap_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.PLAYER_SPELL_AND_TRAP.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        left_most_zone = int(self.center_x - (self.amount_of_zones/2))
        zone_to_update = left_most_zone + zone
        # set the card
        self.set_cell(self.player_spell_and_trap_row, zone_to_update, str(new_zone))

    def set_player_monster_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.PLAYER_MONSTER.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        left_most_zone = int(self.center_x - (self.amount_of_zones/2))
        zone_to_update = left_most_zone + zone
        # set the card
        self.set_cell(self.player_monster_row, zone_to_update, str(new_zone))

    def set_extra_monster_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.EXTRA_MONSTER.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        if zone == 0:
            self.set_cell(self.extra_monster_row, int(self.center_x-1), str(new_zone))
        elif zone == 1:
            self.set_cell(self.extra_monster_row, int(self.center_x+1), str(new_zone))
        else:
            logger.warning(f"Invalid zone: {zone}")

    def set_player_field_spell(self, new_card):
        new_zone = Zone(ZONE_KEYS.PLAYER_SPELL_FIELD, new_card)
        field_spell_zone_on_field = int(self.center_x-3)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.player_monster_row, field_spell_zone_on_field, str(new_zone))

    def set_opponent_field_spell(self, new_card):
        new_zone = Zone(ZONE_KEYS.OPPONENT_SPELL_FIELD, new_card)
        field_spell_zone_on_field = int(self.center_x+3)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.opponent_monster_row, field_spell_zone_on_field, str(new_zone))

    def set_opponent_graveyard_zone(self, zone, new_card):
        graveyard_zone_on_field = int(self.center_x - 3)
        self.set_cell(self.opponent_monster_row, graveyard_zone_on_field, "Empty opponent graveyard")

    def set_player_graveyard_zone(self, zone, new_card):
        graveyard_zone_on_field = int(self.center_x + 3)
        self.set_cell(self.player_monster_row, graveyard_zone_on_field, "Empty player graveyard")

    def set_opponent_banished_zone(self, zone, new_card):
        banished_zone_on_field = int(self.center_x - 4)
        self.set_cell(self.opponent_monster_row, banished_zone_on_field, "Empty opponent banished")

    def set_player_banished_zone(self, zone, new_card):
        banished_zone_on_field = int(self.center_x + 4)
        self.set_cell(self.player_monster_row, banished_zone_on_field, "Empty player banished")

    def set_opponent_deck_zone(self, new_card):
        new_zone = Zone(ZONE_KEYS.OPPONENT_DECK, new_card)
        deck_zone_on_field = int(self.center_x - 3)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.opponent_spell_and_trap_row, deck_zone_on_field, str(new_zone))

    def set_player_deck_zone(self, new_card):
        new_zone = Zone(ZONE_KEYS.PLAYER_DECK, new_card)
        deck_zone_on_field = int(self.center_x + 3)
        self.zones[new_zone.label] = new_zone
        self.set_cell(self.player_spell_and_trap_row, deck_zone_on_field, str(new_zone))

        # do the same for opponent extra deck
    def set_opponent_extra_deck_zone(self, zone, new_card):
        new_zone = Zone(ZONE_KEYS.OPPONENT_EXTRA_DECK.format(zone), new_card)
        self.zones[new_zone.label] = new_zone
        # set the card
        self.set_cell(self.opponent_spell_and_trap_row, int(self.center_x+3), str(new_zone))

    def create_helper_zones(self):
        self.set_cell(int(self.center_y), int(self.center_x-2), "BLANK")
        self.set_cell(int(self.center_y), int(self.center_x-3), "BLANK")
        self.set_cell(int(self.center_y), int(self.center_x+2), "BLANK")
        self.set_cell(int(self.center_y), int(self.center_x+3), "BLANK")
        self.set_cell(int(self.center_y), int(self.center_x), "BLANK")

    def search_player_hand_from_right_to_left(self, factor=0):
        new_col = (self.cols-1) - factor
        cell = self.get_cell(self.player_hand_row, new_col)
        if not cell:
            return self.search_player_hand_from_right_to_left(factor+1)
        else:
            return new_col

    def search_player_hand_from_left_to_right(self, new_col=0):
        cell = self.get_cell(self.player_hand_row, new_col)
        if not cell:
            return self.search_player_hand_from_left_to_right(new_col+1)
        else:
            return new_col
        
    def search_opponent_hand_from_left_to_right(self, new_col=0):
        cell = self.get_cell(self.opponent_hand_row, new_col)
        if not cell:
            return self.search_opponent_hand_from_left_to_right(new_col+1)
        else:
            return new_col

    def search_opponent_hand_from_right_to_left(self, factor=0):
        new_col = (self.cols-1) - factor
        cell = self.get_cell(self.opponent_hand_row, new_col)
        if not cell:
            return self.search_opponent_hand_from_right_to_left(factor+1)
        else:
            return new_col

    def on_key_down(self, event):
        if self.preemtive_key_handler:
            logger.debug("Calling preemtive key handler")
            if self.preemtive_key_handler(self.client, event):
                logger.debug("Preemtive key handler returned True, so we are done")
                return
        key = event.GetKeyCode()
        # handle enter. Perform action on a card.
        if key == wx.WXK_RETURN:
            self.handle_enter()
            return
        # handle space (read all information on card if it's there)
        if key == wx.WXK_SPACE:
            self.handle_space()
            return
        # handle backspace
        if key == wx.WXK_BACK:
            self.handle_backspace()
            return
        # if  it's key down, and we are on the spell and trap row
        # we either need to go to the most left or most right card in the hand
        if key == wx.WXK_DOWN and self.current_row == self.player_spell_and_trap_row:
            if len(self.get_subset_of_zones("ph")) == 0:
                utils.output("No cards in hand")
                return
            cell = self.get_cell(self.player_hand_row, self.current_col)
            if not cell:
                # if we are greater than the center, we need to go to the left
                if self.current_col > self.center_x:
                    new_col = self.search_player_hand_from_right_to_left()
                else:
                    new_col = self.search_player_hand_from_left_to_right()
                self.set_position(self.current_row, new_col)
                return
        elif key == wx.WXK_UP and self.current_row == self.opponent_spell_and_trap_row:
            if len(self.get_subset_of_zones("oh")) == 0:
                utils.output("No cards in hand")
                return
            cell = self.get_cell(self.opponent_hand_row, self.current_col)
            if not cell:
                # if we are greater than the center, we need to go to the left
                if self.current_col > self.center_x:
                    new_col = self.search_opponent_hand_from_right_to_left()
                else:
                    new_col = self.search_opponent_hand_from_left_to_right()
                self.set_position(self.current_row, new_col)
                return
        # perform tab order
        if key == wx.WXK_TAB:
            zone_to_move_to = None
            # check if shift is down (previous)
            if event.ShiftDown():
                zone_to_move_to = self.tab_order.resolve_previous_tab_order()
            else:
                zone_to_move_to = self.tab_order.resolve_next_tab_order()
            if zone_to_move_to:
                old_row = self.current_row
                old_col = self.current_col
                self.set_position_by_name(zone_to_move_to)
                # in this case, the on_cell_change doesn't get called, so we need to call it manually
                self.on_cell_change(old_row, old_col, self.current_row, self.current_col, self.get_cell(self.current_row, self.current_col))
            return
        super(DuelField, self).on_key_down(event)

    def handle_space(self):
        zone = self.get_zone_from_current_position()
        if not zone:
            utils.output("No card found")
            return
        card = zone.card
        if card:
            if isinstance(card, Card):
                utils.output(str(card))
            else:
                utils.output(str(card))
        else:
            utils.output("No card found")

    def handle_backspace(self):
        return duel_menu.show_duel_menu(self.client)

    def handle_enter(self):
        if self.current_row == self.player_spell_and_trap_row and self.current_col == int(self.center_x-3):
            extra_deck_zones = self.get_subset_of_zones("px")
            if len(extra_deck_zones) == 0:
                utils.output("No cards in extra deck")
                return
            self.show_a_card_list("Your extra deck", extra_deck_zones.values())
            return
        if self.current_row == self.player_spell_and_trap_row and self.current_col == int(self.center_x+3):
            utils.output("Player deck")
            return
        if self.current_row == self.player_monster_row and self.current_col == int(self.center_x+3):
            graveyard = self.get_subset_of_zones("pg")
            if len(graveyard) == 0:
                utils.output("No cards in graveyard")
                return
            self.show_a_card_list("Your graveyard", graveyard.values())
            return
        if self.current_row == self.opponent_monster_row and self.current_col == int(self.center_x-3):
            opponent_graveyard = self.get_subset_of_zones("og")
            if len(opponent_graveyard) == 0:
                utils.output("No cards in opponent graveyard")
                return
            self.show_a_card_list("Opponent graveyard", opponent_graveyard.values())
            return
        if self.current_row == self.player_monster_row and self.current_col == int(self.center_x+4):
            banished = self.get_subset_of_zones("pr")
            if len(banished) == 0:
                utils.output("No cards in banished")
                return
            self.show_a_card_list("Your banished cards", banished.values())
            return
        if self.current_row == self.opponent_monster_row and self.current_col == int(self.center_x-4):
            opponent_banished = self.get_subset_of_zones("or")
            if len(opponent_banished) == 0:
                utils.output("No cards in opponent banished")
                return
            self.show_a_card_list("Opponent banished cards", opponent_banished.values())
            return
        if self.current_row == self.opponent_spell_and_trap_row and self.current_col == int(self.center_x+3):
            opponent_extra_deck = self.get_subset_of_zones("ox")
            if len(opponent_extra_deck) == 0:
                utils.output("No cards in opponent extra deck")
                return
            # if all the zones found, is just strings, then it's just face down cards
            if all(isinstance(zone.card, str) for zone in opponent_extra_deck.values()):
                return
            self.show_a_card_list("Opponent extra deck", opponent_extra_deck)
            return
        # now it's just for actions on a card, so if it's not our turn, do nothing
        if not self.client.is_it_my_turn:
            return
        zone = self.get_zone_from_current_position()
        if not zone:
            return
        action_menu.show_action_menu_for_zone(self.client, zone)
        
    def show_a_card_list(self, title, zones):
        zones = list(zones)
        cards = [zone.card for zone in zones]
        cl = card_list_ui.HorizontalCardList(self.client, title, cards)
        index = cl.select_card()
        if index == -1:
            return
        print(f"Selected index: {index}")
        zone_selected = zones[index]
        print(zones)
        print(zone_selected)
        # todo: maybe find another palce to do it
        # but for now, if we have activatable or chaining cards on the player
        # see if the selected card is in it
        if zone_selected.card in self.client.player.chaining_cards:
            self.resolve_chain(zone_selected)
        else:
            action_menu.show_action_menu_for_zone(self.client, zone_selected)
        return zone_selected


# handlers that are not duel messages but are somewhat related to within the duel
@utils.packet_handler(structs.ServerIdType.TIME_LIMIT)
def handle_time_limit_announcement(client, packet_data, packet_length):
    time_limit = structs.StocTimeLimit.from_buffer_copy(packet_data)
    # check if player has been set
    if not client.player:
        return
    if time_limit.team != client.what_player_am_i:
        return
    if time_limit.time > 0:
        client.player.turn_timer = time_limit.time
