import io
import struct

from game.card.card import Card
from game.card import card_constants
from game.edo import structs

from core import utils
from ui.base_ui import VerticalMenu

@utils.duel_message_handler(19)
def msg_select_position(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    code = client.read_u32(data)
    card = Card(code)
    positions = card_constants.POSITION(client.read_u8(data))
    select_position(client, player, card, positions)

def select_position(client, player, card, positions):
    positions_menu = VerticalMenu(f"Select position for {card.get_name()}:")
    if positions & card_constants.POSITION.FACE_UP_ATTACK:
        positions_menu.append_item("Face-up attack", function=lambda: set_position(client, 1))
    if positions & card_constants.POSITION.FACE_DOWN_ATTACK:
        positions_menu.append_item("Face-down attack", function=lambda: set_position(client, 2))
    if positions & card_constants.POSITION.FACE_UP_DEFENSE:
        positions_menu.append_item("Face-up defense", function=lambda: set_position(client, 4))
    if positions & card_constants.POSITION.FACE_DOWN_DEFENSE:
        positions_menu.append_item("Face-down defense", function=lambda: set_position(client, 8))
    utils.get_ui_stack().push_ui(positions_menu)

def set_position(client, pos):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', pos))

