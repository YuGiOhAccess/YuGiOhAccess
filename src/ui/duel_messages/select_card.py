import io
import logging
import struct

import wx

from game.card.card import Card
from game.card import card_constants
from game.card.location_conversion import LocationConversion
from game.edo import structs

from ui.base_ui import VerticalMenu

from core import utils

logger = logging.getLogger(__name__)

@utils.duel_message_handler(20)
def msg_select_tribute(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    cancelable = client.read_u8(data)
    min = client.read_u32(data)
    max = client.read_u32(data)
    size = client.read_u32(data)
    cards = []
    for i in range(size):
        code = client.read_u32(data)
        card = Card(code)
        # in this case, we can't use the client.read_location, because it doesn't send the position regardless of what it is
        card.controller = client.read_u8(data)
        card.location = client.read_u8(data)
        card.sequence = client.read_u32(data)
        card.release_param = client.read_u8(data)
        cards.append(card)
    select_tribute(client, player, cancelable, min, max, cards)

@utils.duel_message_handler(15)
def msg_select_card(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    cancelable = client.read_u8(data)
    min = client.read_u32(data)
    max = client.read_u32(data)
    size = client.read_u32(data)
    cards = []
    logger.debug(f"Size: {size}")
    for i in range(size):
        code = client.read_u32(data)
        logger.debug(f"Code: {code}")
        controller, location, sequence, position = client.read_location(data)
        if code != 0:
            card = Card(code)
            card.set_location_and_position_info(controller, location, sequence, position)
            cards.append(card)
        else:
            card = Card(0)
            card.controller = controller
            card.location = location
            card.sequence = sequence
            card.position = card_constants.POSITION(position)
            cards.append(card)
    select_card(client, player, cancelable, min, max, cards)

def select_card(client, player, cancelable, min_cards, max_cards, cards, is_tribute=False):
    # figure out if any of the cards are on the field.
    presentable_cards = []
    for selectable_card in cards:
        location_information = LocationConversion.from_card_location(client, selectable_card)
        if selectable_card.code != 0:
            presentable_cards.append(f"{selectable_card.get_name()} in {location_information.to_human_readable()}")
        else:
            presentable_cards.append(f"Face down card in {location_information.to_human_readable()}")
    show_menu_with_presentable_cards(client, cards, presentable_cards, min_cards, max_cards, is_tribute)



def select_tribute(client, *args, **kwargs):
    kwargs['is_tribute'] = True
    select_card(client, *args, **kwargs)

def show_menu_with_presentable_cards(client, cards, presentable_cards, min_cards, max_cards, is_tribute):
    question = f"Select {min_cards} to {max_cards} card(s)"
    if is_tribute:
        question = f"Select {min_cards} to {max_cards} card(s) as tribute"
    select_card_menu = VerticalMenu(question)
    select_card_menu.append_item(question)
    for card in presentable_cards:
        select_card_menu.append_item(wx.CheckBox, label=card)
    select_card_menu.append_item("Finish", function=lambda: finish_card_selection(client, select_card_menu, cards, min_cards, max_cards, is_tribute))
    utils.get_ui_stack().push_ui(select_card_menu)

def finish_card_selection(client, select_card_menu, cards, min_cards, max_cards, is_tribute):
    card_checkboxes = []
    for row in select_card_menu.cells:
        if isinstance(row[0], wx.CheckBox):
            card_checkboxes.append(row[0])
    if len(cards) == len(card_checkboxes):
        print("Success1")
    selected_cards = []
    for i, checkbox in enumerate(card_checkboxes):
        if checkbox.IsChecked():
            selected_cards.append(i)
    logger.debug(f"Selected cards:\nLength: {len(selected_cards)}\n{selected_cards}")
    buf = b""
    # pack an uint with the value of 1, to signal to the server
    buf += struct.pack('I', 1)
    # first pack the size of the selected cards into an uint32
    buf += struct.pack('I', len(selected_cards))
    for selected_card_index in selected_cards:
        # add the index to the buffer, as an uint16
        buf += struct.pack('H', selected_card_index)
    utils.get_ui_stack().pop_ui()
    print(buf)
    client.send(structs.ClientIdType.RESPONSE, buf)
