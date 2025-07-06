import io
import logging

from core import utils

logger = logging.getLogger(__name__)

@utils.duel_message_handler(96)
def msg_card_target(client, data, data_length, cancelled=False):
    data = io.BytesIO(data[1:])
    controller, location, sequence, position = client.read_location(data)
    target_controller, target_location, target_sequence, target_position = client.read_location(data)
    card = client.get_card(controller, location, sequence)
    target = client.get_card(target_controller, target_location, target_sequence)
    if not card or not target:
        logger.error(f"Card or target not found\nCard info: {controller}, {location}, {sequence}\nTarget info: {target_controller}, {target_location}, {target_sequence},\Found card from duel field: {card}\nFound target from duel field: {target}")
    card_target(client, card, target, cancelled)

@utils.duel_message_handler(97)
def msg_cancel_card_target(client, data, data_length):
    return msg_card_target(client, data, data_length, True)

def card_target(client, card, target, cancelled):
    if not cancelled:
        utils.output("%s targets %s." % (card.get_name(), target.get_name()))
        utils.get_ui_stack().play_duel_sound_effect("aim")
    else:
        utils.output("%s cancels targeting %s." % (card.get_name(), target.get_name()))


