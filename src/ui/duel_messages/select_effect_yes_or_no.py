import io
import struct

from game.card.card import Card
from game.edo import structs

from core import utils

from ui.base_ui import VerticalMenu

@utils.duel_message_handler(12)
def msg_select_effectyn(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    card = Card(client.read_u32(data))
    controller, location, seq, pos = client.read_location(data)
    card.set_location_and_position_info(controller, location, seq, pos)
    desc = client.read_u64(data)
    select_effectyn(client, player, card, desc)

def select_effectyn(client, player, card, desc):
    yes_or_no_menu = VerticalMenu("")
    question = f"Do you want to use {card.get_name()}'s effect?"
    s = card.get_effect_description(desc, True)
    if s:
        question += f"\n{s}"
    yes_or_no_menu.append_item(question, function=lambda: utils.output(str(card)))
    yes_or_no_menu.append_item("Yes", function=lambda: yes(client))
    yes_or_no_menu.append_item("No", function=lambda: no(client))
    utils.get_ui_stack().push_ui(yes_or_no_menu)



def yes(client):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 1))    

def no(client):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', 0))    
