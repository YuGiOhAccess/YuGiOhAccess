import struct

from ui.base_ui import HorizontalMenu, StatusMessageWithoutTimelimit
from core import utils

from game.edo import structs

@utils.packet_handler(structs.ServerIdType.REMATCH_WAIT)
def handle_rematch_wait(client, packet_data, packet_length):
    pass

@utils.packet_handler(structs.ServerIdType.REMATCH)
def handle_rematch(client, packet_data, packet_length):
    return show_rematch_ui(client)

@utils.ui_function
def show_rematch_ui(client):
    rematch_menu = HorizontalMenu("Do you want to rematch?")
    rematch_menu.append_item("Yes", lambda: _rematch_yes(client))
    rematch_menu.append_item("No", lambda: _rematch_no(client))
    return rematch_menu

@utils.ui_function
def _rematch_yes(client):
    client.send(structs.ClientIdType.REMATCH, struct.pack("B", 1))
    sm = StatusMessageWithoutTimelimit("Waiting for opponent")
    return sm

@utils.ui_function
def _rematch_no(client):
    client.send(structs.ClientIdType.REMATCH, struct.pack("B", 0))
    sm = StatusMessageWithoutTimelimit("Waiting for opponent")
    return sm
