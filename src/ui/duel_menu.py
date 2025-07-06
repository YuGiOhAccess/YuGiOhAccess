import struct

from game.edo import structs
from ui.base_ui import VerticalMenu
from core import utils

from game.card import card_constants

def show_duel_menu(client):
    phase_str = card_constants.PHASES.get(client.current_phase, str(client.current_phase))
    backspace_menu = VerticalMenu("Duel Menu")
    # items to put there, if it's my turn
    if client.is_it_my_turn:
        backspace_menu.append_item(f"{phase_str}, your turn. {client.player.lifepoints} / {client.player.opponent_lifepoints} lifepoints. {client.player.turn_timer.get_remaining_time()} seconds remaining. Turn {client.turn_count}")
        if client.player.can_go_to_battle_phase:
            backspace_menu.append_item("Battle phase", function=lambda: send_battle_phase(client))
        if client.player.can_go_to_main_phase2:
            backspace_menu.append_item("Main phase 2", function=lambda: send_main_phase2(client))
        if client.player.can_go_to_end_phase:
            backspace_menu.append_item("End turn", function=lambda: send_end_phase(client))
    else:
        backspace_menu.append_item(f"{phase_str}, Opponents turn. {client.player.lifepoints} / {client.player.opponent_lifepoints} lifepoints. Turn {client.turn_count}")
    backspace_menu.append_item("Close", lambda: utils.get_ui_stack().pop_ui())
    utils.get_ui_stack().push_ui(backspace_menu)

def send_battle_phase(client):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 6))

def send_main_phase2(client):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 2))

def send_end_phase(client):
    utils.get_ui_stack().pop_ui()
    if client.current_phase == 4 or client.current_phase == 0x100: # main phase 1 or main phase 2
        client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 7))
    if client.current_phase == 8 or client.current_phase == 0x80: # battle phase
        client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 3))
