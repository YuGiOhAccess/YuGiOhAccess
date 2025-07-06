import logging
from pathlib import Path
import random

import wx
import requests
from core import utils
from core import variables

from game.edo import banlists, structs, structs_utils
from game.card.card import Card

from game.card import ydke
from ui.base_ui import VerticalMenu, DynamicVerticalMenu, StatusMessage
from ui import server_ui

logger = logging.getLogger(__name__)

@utils.packet_handler(structs.ServerIdType.CREATE_GAME)
def handle_create_game(client, packet_data, packet_length):
    message = structs.StocCreateGame.from_buffer_copy(packet_data)
    try:
        utils.output(f"Created room with ID {message.id} and password {client.memory.room_password}")
    except AttributeError:
        utils.output(f"Created room with ID {message.id}")

@utils.packet_handler(structs.ServerIdType.JOIN_GAME)
def handle_join_game(client, packet_data, packet_length):
    utils.output("Joined game")
    client.memory.users_info = []
    if variables.DEV_OPTIONS.deck:
        path = Path(variables.DECK_DIR / f"{variables.DEV_OPTIONS.deck}.json")
        if path.exists():
            handle_deck_menu_select_deck(client, path)
        else:
            utils.output(f"Deck {variables.DEV_OPTIONS.deck} not found")
    if variables.DEV_OPTIONS.bot:
        if variables.DEV_OPTIONS.botdeck:
            # capitalize the first letter of the bot deck
            deck = variables.DEV_OPTIONS.botdeck[0].upper() + variables.DEV_OPTIONS.botdeck[1:]
            add_bot_to_room(client, deck)
        else:
            add_bot_to_room(client)
    return display_room_menu(client)

@utils.packet_handler(structs.ServerIdType.PLAYER_ENTER)
def handle_player_enter(client, packet_data, packet_length):
    result = structs.StocPlayerEnter.from_buffer_copy(packet_data)
    player_name = structs_utils.u16_to_string(result.name)
    client.memory.users_info.append({"name": player_name, "ready": False, "host": False, "position": result.pos})
    utils.output(f"{player_name} entered the room at position {result.pos}")

@utils.packet_handler(structs.ServerIdType.PLAYER_CHANGE)
def handle_player_change(client, packet_data, packet_length):
    result = structs.StocPlayerChange.from_buffer_copy(packet_data)
    team = result.position()
    is_ready = result.is_ready()
    for user in client.memory.users_info:
        if user["position"] == team:
            user["ready"] = is_ready
    utils.output(f"Team {team} is {'ready' if is_ready else 'not ready'}")

@utils.packet_handler(structs.ServerIdType.TYPE_CHANGE)
def handle_type_change(client, packet_data, packet_length):
    result = structs.StocTypeChange.from_buffer_copy(packet_data)
    team = result.position()
    is_host = result.is_host()
    for user in client.memory.users_info:
        if user["position"] == team:
            user["host"] = is_host
    utils.output(f"Team {team} is {'host' if is_host else 'not host'}")

@utils.ui_function
def display_room_menu(client):
    utils.get_ui_stack().clear_ui_stack()
    logger.debug("Displaying room menu")
    room = client.room
    room_menu = DynamicVerticalMenu("Room Menu")
    basic_room_information = f"Room ID: {room.roomid}.\n"
    if room.needpass:
        basic_room_information += f"Password: {client.memory.room_password}.\n"
    else:
        basic_room_information += "Password: None.\n"
    if room.roomnotes:
        basic_room_information += f"{room.roomnotes}.\n"
    banlist_manager = banlists.BanlistManager()
    banlist = banlist_manager.get_banlist_by_hash(room.banlist_hash)
    basic_room_information += f"Banlist: {banlist.name}.\n"
    room_menu.append_item(basic_room_information)
    # show the players in the room.
    room_menu.append_item(lambda client=client: resolve_players(client))
    #participants.Bind(wx.EVT_SET_FOCUS, lambda e: utils.output(resolve_players(client)))
    if client.memory.is_host and len(client.room.users) < 2:
        room_menu.append_item("Add a bot opponent", lambda: handle_add_bot_as_opponent(client))
    room_menu.append_item("Select/import Deck", lambda: handle_room_menu_select_deck(client))
    if client.memory.is_host:
        room_menu.append_item("Start", lambda: handle_room_menu_ready_or_start(client))
    else:
        room_menu.append_item("Ready", lambda: handle_room_menu_ready_or_start(client))
    room_menu.append_item("Back", lambda: handle_me_disconnect(client))
    utils.get_discord_presence_manager().update_presence(
        state="In a room",
        details="Waiting for an opponent",
        party_size=[len(client.room.users), 2],
    )
    return room_menu

def resolve_players(client):
    users = client.room.users
    names = [team["name"] for team in users]
    new_memory = []
    for team in client.memory.users_info:
        if team["name"] not in names:
            continue
        team["position"] = users[names.index(team["name"])]["pos"]
        new_memory.append(team)
    client.memory.users_info = new_memory
    player_and_position = ""
    for team in client.memory.users_info:
        player_and_position += f"Team {team['position']} - {team['name']} "
        if team["host"]:
            player_and_position += "(host) "
        player_and_position += "is ready\n" if team["ready"] else "is not ready\n"
    return player_and_position

def handle_room_menu_ready_or_start(client):
    if not hasattr(client.memory, "deck"):
        sm = StatusMessage("You must select a deck first", lambda: display_room_menu(client))
        sm.show()
        return
    client.send(structs.ClientIdType.READY)
    if client.memory.is_host:
        client.send(structs.ClientIdType.TRY_START)

@utils.ui_function
def handle_room_menu_select_deck(client):
    # make a menu with name, public decks, my decks, and the import options
    deck_menu = VerticalMenu("Select Deck")
    deck_menu.append_item("Public Decks", lambda: handle_room_menu_show_deck_menu(client, "Public Decks", variables.LOCAL_DATA_DIR / "decks"))
    deck_menu.append_item("My Decks", lambda: handle_room_menu_show_deck_menu(client, "My Decks", variables.DECK_DIR))
    deck_menu.append_item("Import deck from deck string", lambda: handle_import_deck_show_menu(client))
    deck_menu.append_item("Import all decks from YuGiOh MUD", lambda: handle_import_all_decks(client))
    deck_menu.append_item("Back", lambda: display_room_menu(client))
    return deck_menu

@utils.ui_function
def handle_room_menu_show_deck_menu(client, name, deck_dir):
    if not deck_dir.exists():
        logger.debug(f"Creating deck directory {deck_dir}")
        deck_dir.mkdir(parents=True, exist_ok=True)
    deck_menu = VerticalMenu(name)
    # loop through all files found in variables.DECK_DIR
    for deck_file in deck_dir.iterdir():
        # give full path to the deck file
        deck_menu.append_item(deck_file.stem, lambda deck_file=deck_file: handle_deck_menu_select_deck(client, deck_file))
    deck_menu.append_item("Back", lambda: handle_room_menu_select_deck(client))
    return deck_menu

@utils.ui_function
def handle_import_all_decks(client):
    # make a menu
    deck_menu = VerticalMenu("Import all decks")
    # add a text that describes what's happening
    deck_menu.append_item("This will import all the decks you have from the AllInAccess YuGiOh MUD!", lambda: None)
    deck_menu.append_item("This will remove all current decks you have!", lambda: None)
    deck_menu.append_item("To continue, please put in your MUD username and password", lambda: None)
    # add 2 text boxes for the username and password
    username_input = deck_menu.append_item(wx.TextCtrl, label="Username")
    password_input = deck_menu.append_item(wx.TextCtrl, label="Password")
    # add a button that will call the function that will import the decks
    deck_menu.append_item("Import", lambda: handle_import_all_decks_import(client, username_input.GetValue(), password_input.GetValue()))
    deck_menu.append_item("Back", lambda: handle_room_menu_select_deck(client))
    return deck_menu

def handle_import_all_decks_import(client, username, password):
    if not username:
        sm = StatusMessage("You must provide a username", lambda: handle_import_all_decks(client))
        sm.show()
        return
    if not password:
        sm = StatusMessage("You must provide a password", lambda: handle_import_all_decks(client))
        sm.show()
        return
    # get the list of decks from the MUD
    url = "https://allinaccess.com/game/decklist.php"
    logger.debug(f"Getting decks from {url}")
    result = requests.post(url, data={"username": username, "password": password})
    body = result.json()
    if result.status_code != 200 or "error" in body:
        logger.warning(f"Unable to import decks: {result.status_code} {body}")
        sm = StatusMessage("Unable to import decks: %s" % body["error"], lambda: handle_import_all_decks(client))
        sm.show()
        return
    amount_of_decks_to_import = len(body)
    if amount_of_decks_to_import == 0:
        sm = StatusMessage("No decks to import", lambda: handle_room_menu_select_deck(client))
        sm.show()
        return
    logger.debug(f"Got {amount_of_decks_to_import} decks")
    logger.debug("Removing all current decks")
    for deck_file in variables.DECK_DIR.iterdir():
        deck_file.unlink()
    logger.debug("Importing decks")
    for deck_info in body:
        logger.debug(f"Importing deck: {deck_info['name']} {deck_info['url']}")
        deck = ydke.Deck.from_ydke(deck_info["url"])
        deck_file = Path(variables.DECK_DIR / f"{utils.sanitize_filename(deck_info['name'])}.json")
        with open(deck_file, "w") as f:
            f.write(deck.to_json())
    # if amount_of_decks_to_import is not equal to the amount of files in the decks folder, show an error
    if amount_of_decks_to_import != len(list(variables.DECK_DIR.iterdir())):
        logger.warning(f"Not all decks were imported: {amount_of_decks_to_import} != {len(list(variables.DECK_DIR.iterdir()))}")
        sm = StatusMessage("Unable to import all decks - only some were imported.", lambda: handle_room_menu_select_deck(client))
        sm.show()
        return
    logger.debug("Decks imported")
    sm = StatusMessage("%s decks imported" % amount_of_decks_to_import, lambda: handle_room_menu_select_deck(client))
    sm.show()



@utils.ui_function
def handle_deck_menu_select_deck(client, deck_file):
    logger.debug(f"Loading deck {str(deck_file)}")
    utils.output(f"Loading deck {deck_file.stem}")
    with open(deck_file, "r") as f:
        # if the file ends in json do it from json, if it ends in ydke do it from ydke
        if deck_file.suffix == ".ydke":
            parsed_deck = ydke.Deck.from_ydke(f.read())
            logger.debug(f"Deck: {parsed_deck}")
        else:
            parsed_deck = ydke.Deck.from_json(f.read())
            logger.debug(f"Deck: {parsed_deck}")
        # check against room banlist
        banlist_manager = banlists.BanlistManager()
        banlist = banlist_manager.get_banlist_by_hash(client.room.banlist_hash)
        is_allowed, reason = banlist.is_deck_allowed(parsed_deck)
        logger.debug(f"Deck is allowed: {is_allowed} {reason}")
        if not is_allowed:
            # convert the reason into a string
            banned_deck_message = VerticalMenu("Deck is not allowed")
            banned_deck_message.append_item("Deck is not allowed", lambda: None)
            for card_code, card_info in reason.items():
                card = Card(card_code)
                banned_deck_message.append_item(f"{card.name} is limited to {card_info.limit} and you have {card_info.found} in your deck.\n", lambda: None)
            banned_deck_message.append_item("Back", lambda: handle_room_menu_select_deck(client))
            return banned_deck_message
        deck = structs.Deck()
        deck.set_main_deck(parsed_deck.cards)
        deck.set_side_deck(parsed_deck.side)
        client.send(structs.ClientIdType.UPDATE_DECK, deck)
        client.memory.deck = deck
        utils.output(f"Deck {deck_file.stem} loaded")
        display_room_menu(client)
        return

@utils.ui_function
def handle_import_deck_show_menu(client):
    # it should be a vertical menu, with 2 input boxes. Name and ydke deck string
    deck_import_menu = VerticalMenu("Import Deck")
    name_input = deck_import_menu.append_item(wx.TextCtrl, label="Deck name")
    deck_input = deck_import_menu.append_item(wx.TextCtrl, label="YDKE Deck string")
    deck_import_menu.append_item("Import", lambda: handle_deck_import_import_deck(client, name_input.GetValue(), deck_input.GetValue()))
    deck_import_menu.append_item("Back", lambda: handle_room_menu_select_deck(client))

def handle_deck_import_import_deck(client, name, deck_string):
    if not name:
        sm = StatusMessage("You must provide a name for the deck", lambda: handle_import_deck_show_menu(client))
        sm.show()
        return
    # name cannot contain spaces, or any chars that are not a-<A->z0-9
    if not name.isalnum():
        sm = StatusMessage("Deck name can only contain letters and numbers", lambda: handle_import_deck_show_menu(client))
        sm.show()
        return
    if not deck_string:
        sm = StatusMessage("You must provide a deck string", lambda: handle_import_deck_show_menu(client))
        sm.show()
        return
    # if the deck string doesn't start with ydke, show an error
    if not deck_string.startswith("ydke"):
        sm = StatusMessage("Deck string doesn't seem to be a valid deck string", lambda: handle_import_deck_show_menu(client))
        sm.show()
        return
    try:
        deck = ydke.Deck.from_ydke(deck_string)
    except ydke.URLParseError:
        sm = StatusMessage("Deck string doesn't seem to be a valid deck string", lambda: handle_import_deck_show_menu(client))
        sm.show()
        return
    # save the deck to a file in the decks folder
    deck_file = Path(variables.DECK_DIR / f"{name}.json")
    with open(deck_file, "w") as f:
        f.write(deck.to_json())
    sm = StatusMessage(f"Deck {name} imported", lambda: handle_room_menu_select_deck(client))
    sm.show()


def handle_add_bot_as_opponent(client):
    utils.get_ui_stack().clear_ui_stack()
    if len(client.room.users) >= 2:
        sm = StatusMessage("There are already 2 players in the room", lambda: display_room_menu(client))
        sm.show()
        return
    ## get the list of available decks
    url = "https://updates.yugiohaccess.com/bot/decks"
    result = requests.get(url)
    if result.status_code != 200:
        sm = StatusMessage("Unable to add a bot at this time.", lambda: display_room_menu(client))
        sm.show()
        return
    # if the body contains a status field and it's not success it failed for some reason
    result = result.json()
    if "status" in result and result["status"] != "success":
        sm = StatusMessage("Unable to add a bot at this time.", lambda: display_room_menu(client))
        sm.show()
        return
    logger.debug(f"Got the list of decks: {result['decks']}")
    # create a vertical menu with the list of decks
    bot_menu = VerticalMenu("Select bot deck")
    bot_menu .append_item("Random", lambda: add_bot_to_room(client, "", result["decks"]))
    for deck in result["decks"]:
        bot_menu.append_item(deck, lambda deck=deck: add_bot_to_room(client, deck, result["decks"]))
    bot_menu.append_item("Back", lambda: display_room_menu(client))
    utils.get_ui_stack().push_ui(bot_menu)


def add_bot_to_room(client, deck="", available_decks=[]):
    if len(client.room.users) >= 2:
        sm = StatusMessage("There are already 2 players in the room", lambda: display_room_menu(client))
        sm.show()
        return
    url = f"https://updates.yugiohaccess.com/bot/join?host={client.server.address}&port={client.server.lobby_port}&roomid={client.room.roomid}"
    if deck:
        url += f"&deck={deck}"
    else:
        random_deck = random.choice(available_decks)
        url += f"&deck={random_deck}"
    if client.room.needpass:
        url += f"&password={client.memory.room_password}"
    # handle rock paper scissors bot behavior
    rock_paper_scissors_bot_behavior = variables.config.get("rock_paper_scissors_bot_behavior")
    if rock_paper_scissors_bot_behavior == "rock":
        url += "&hand=2"
    elif rock_paper_scissors_bot_behavior == "paper":
        url += "&hand=3"
    elif rock_paper_scissors_bot_behavior == "scissors":
        url += "&hand=1"
    # if enable_bot_chat is false in the config, disable bot chat
    if not variables.config.get("enable_bot_chat"):
        url += "&chat=false"
    logger.debug(f"Adding bot to room with url {url}")
    result = requests.get(url)
    if result.status_code != 200:
        sm = StatusMessage("Unable to add a bot at this time.", lambda: display_room_menu(client))
        sm.show()
        return
    # if the body contains a status field and it's not success it failed for some reason
    if "status" in result.json() and result.json()["status"] != "success":
        sm = StatusMessage("Unable to add a bot at this time.", lambda: display_room_menu(client))
        sm.show()
        return
    utils.get_ui_stack().clear_ui_stack()
    utils.output("Bot added to room")
    return display_room_menu(client)


def handle_me_disconnect(client):
    # we should probably send a packet here, but don't know if it's needed, or if closing the socket is enough.
    client.disconnect()
    return server_ui.server_main_menu(client.server)
