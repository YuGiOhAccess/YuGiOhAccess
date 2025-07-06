import io
import logging

from game.card.location_conversion import LocationConversion

from core import utils

logger = logging.getLogger(__name__)

@utils.duel_message_handler(64)
def msg_flipsummoning(client, data, data_length):
    data = io.BytesIO(data[1:])
    code = client.read_u32(data)
    controller, location, sequence, position = client.read_location(data)
    card = client.get_card(controller, location, sequence)
    flipsummoning(client, card, controller, location, sequence, position)

@utils.duel_message_handler(65)
def msg_flipsummoned(client, data, data_length):
    data = io.BytesIO(data[1:])
    #don't know if this actually have any data, so let's just log it for now
    logger.debug("Flip summoned")
    logger.debug(data.read())

def flipsummoning(client, card, controller, location, sequence, position):
    if isinstance(card, str):
        lc = LocationConversion(client, controller, location, sequence)
        utils.output(f"{lc.to_human_readable()} Was flip summoned.")
        return
    if card.controller == client.what_player_am_i:
        utils.output(f"You flip summon {card.get_name()}")
    else:
        utils.output(f"Your opponent flip summons {card.get_name()}")

