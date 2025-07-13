import wx
import logging
from core import utils
from game.servers import get_servers
from ui.base_ui import InputUI, StatusMessage, VerticalMenu, WaitUI, NumberInputUI

from game.client import Client
from game.edo import banlists

from core import variables
logger = logging.getLogger(__name__)

@utils.ui_function
def server_selection_menu():
    servers = get_servers()
    if isinstance(variables.DEV_OPTIONS.server, int):
        server = servers[variables.DEV_OPTIONS.server]
        logger.debug(f"Connecting to {server}")
        server_main_menu(server)
        return
    server_selection_menu = VerticalMenu("Server Menu")
    for server in servers:
        server_selection_menu.append_item(server.name, lambda server=server: server_main_menu(server))
    server_selection_menu.append_item("Back", utils.get_main_menu_function)
    return server_selection_menu

@utils.ui_function
def server_main_menu(server):
    wait_ui = WaitUI("Connecting to server", server.is_available)
    result = wait_ui.show()
    if not result:
        sm = StatusMessage("Server is not available", server_selection_menu)
        sm.show()
        return
    # we know we can connect to the server. It's stored in the server variable.
    # make a menu to either create a room or join a room
    if variables.DEV_OPTIONS.action:
        if variables.DEV_OPTIONS.action == "create":
            create_room_on_server(server, {
                "name": "",
                "password": variables.DEV_OPTIONS.password or "",
                "notes": "",
            })
            return
        if variables.DEV_OPTIONS.action == "join":
            join_room_final(server, variables.DEV_OPTIONS.id, variables.DEV_OPTIONS.password)
            return
    utils.get_discord_presence_manager().update_presence(
        state=f"Connected to {server.name}"
    )
    room_menu = VerticalMenu(f"Connected to {server.name}")
    room_menu.append_item("Create Room", lambda: create_room(server))
    room_menu.append_item("Join Room", lambda: join_room_ask_for_id(server))
    room_menu.append_item("List Rooms", lambda: list_rooms(server))
    room_menu.append_item("Disconnect", server_selection_menu)
    return room_menu

@utils.ui_function
def create_room(server):
    banlist_manager = banlists.BanlistManager()
    # we know we can connect to the server. It's stored in the server variable.
    room_menu = VerticalMenu("Room Settings")
    room_menu.append_item("Room Settings", None)
    notes = room_menu.append_item(wx.TextCtrl, None, label="Room notes")
    password = room_menu.append_item(wx.TextCtrl, None, label="Room password (leave empty to make a public room)", style=wx.TE_PASSWORD)
    # make a banlist wx.Choice
    banlist = room_menu.append_item(wx.Choice, label="Banlist", choices=banlist_manager.get_banlist_names())
    # make a key handler, so when left or right arrow is pressed, it changes the banlist
    banlist.Bind(wx.EVT_KEY_DOWN, lambda event: banlist_change_choice(event, banlist))
    banlist.SetSelection(0)
    # make a button to create the room
    room_menu.append_item("Create Room", lambda: create_room_on_server(server, {
        "name": "",
        "password": password.GetValue(),
        "notes": notes.GetValue().strip(),
        "banlist": banlist.GetString(banlist.GetSelection()),
    }))
    room_menu.append_item("Back", lambda: server_main_menu(server))
    return room_menu

def banlist_change_choice(event, choicer):
    # if key is left arrow, go to the previous choice
    if event.GetKeyCode() == wx.WXK_LEFT:
        new_choice = choicer.GetSelection() - 1
        if new_choice < 0:
            new_choice = choicer.GetCount() - 1
        choicer.SetSelection(new_choice)
        utils.output(choicer.GetString(choicer.GetSelection()))
    # if key is right arrow, go to the next choice
    if event.GetKeyCode() == wx.WXK_RIGHT:
        new_choice = choicer.GetSelection() + 1
        if new_choice >= choicer.GetCount():
            new_choice = 0
        choicer.SetSelection(new_choice)
        utils.output(choicer.GetString(choicer.GetSelection()))
    else:
        event.Skip()

def create_room_on_server(server, room_settings):
    logger.debug(f"Creating room with settings {room_settings} on {server}")
    c = Client.create_room(server, room_settings)
    if not c:
        return
    logger.debug(f"Created room {c}")
    # store the password in memory if we need it later
    if room_settings["password"]:
        c.memory.room_password = room_settings["password"]
    c.memory.is_host = True
    # the room will automatically be shown, by packets being received.

def join_room_ask_for_id(server):
    # ask for the room id, keeping in mind that it should be a number
    room_id_input = NumberInputUI("Enter room id")
    room_id = room_id_input.show()
    if not room_id:
        server_main_menu(server)
        return
    join_room(server, room_id)

@utils.ui_function
def list_rooms(server):
    rooms = server.list_rooms()
    # exclude any rooms from the list that are not waiting
    rooms = [room for room in rooms if room.istart == "waiting"]
    if not rooms:
        sm = StatusMessage("No rooms available", lambda: server_main_menu(server))
        sm.show()
        return
    room_menu = VerticalMenu(f"Rooms on {server.name}")
    for room in rooms:
        if room.istart != "waiting":
            continue
        room_printable = f"{room.roomid}, "
        if room.needpass:
            room_printable += "(needs password), "
        if room.roomname:
            room_printable += f" name: {room.roomname}, "
        if room.roomnotes:
            room_printable += f"notes: {room.roomnotes}, "
        room_printable += f"{room.team1} vs {room.team2}, "
        if room.best_of == 3:
            room_printable += "match, "
        room_printable += f"Players: {room.print_players()}"
        room_printable += f"Time limit: {round(room.time_limit/60, 2)} minutes, "
        if room.start_lp != 8000:
            room_printable += f"Starting LP: {room.start_lp}, "
        if room.start_hand != 5:
            room_printable += f"Starting hand: {room.start_hand}, "
        if room.draw_count != 1:
            room_printable += f"Draw count: {room.draw_count}, "
        room_menu.append_item(room_printable, lambda room=room: join_room(server, room.roomid))
    room_menu.append_item("Back", lambda: server_main_menu(server))
    return room_menu

def join_room(server, id, password=None):
    logger.debug(f"Joining room {id} on {server}")
    room = server.get_room(id)
    if not room:
        sm = StatusMessage("Room not found", lambda: server_main_menu(server))
        sm.show()
        return
    logger.debug(f"Room found: {room}")
    if room.istart != "waiting":
        sm = StatusMessage("Room is not waiting", lambda: server_main_menu(server))
        sm.show()
        return
    if room.needpass and not password:
        logger.debug("Room needs password")
        password_input = InputUI("Enter room password")
        password = password_input.show()
        if not password:
            logger.debug("No password entered")
            server_main_menu(server)
            return
    # if there's more than 1 player in the room, we can't join
    if len(room.users) > 1:
        sm = StatusMessage("Room is full", lambda: server_main_menu(server))
        sm.show()
        return
    logger.debug(f"Joining room {room}")
    join_room_final(server, room.roomid, password)

def join_room_final(server, id, password):
    c = Client.join_room(server, id, password)
    if not c:
        sm = StatusMessage("Password incorrect", lambda: server_main_menu(server))
        sm.show()
        return
    c.memory.is_host = False
    c.memory.room_password = password
    logger.info(f"Joined room {c}")
