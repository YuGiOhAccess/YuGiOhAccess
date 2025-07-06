import io

from core import utils
from core import variables

from game.card.card import Card
from game.card import card_constants

import logging

logger = logging.getLogger(__name__)

@utils.duel_message_handler(60)
def msg_summoning(client, data, data_length, special=False):
    data = io.BytesIO(data[1:])
    code = client.read_u32(data)
    card = Card(code)
    controller, location, sequence, position = client.read_location(data)
    logger.debug(f"Position: {position}")
    card.set_location_and_position_info(controller, location, sequence, card_constants.POSITION(position))
    summoning(client, card, controller, location, sequence, position, special=special)
    return data.read()

@utils.duel_message_handler(61)
@utils.duel_message_handler(63)
def msg_summoned(client, data, data_length):
    return data[1:]

@utils.duel_message_handler(62)
def msg_summoning_special(client, data, data_length):
    msg_summoning(client, data, data_length, special=True)

def summoning(client, card, controller, location, sequence, position, special=False):
    card.set_location_and_position_info(controller, location, sequence, card_constants.POSITION(position))
    print(card.position)
    _player = ""
    if card.controller == client.what_player_am_i:
        _player = "You"
    else:
        _player = "Your opponent"
    if special:
        if card.type & card_constants.TYPE.LINK:
             utils.output(variables.LANGUAGE_HANDLER._("%s special summoning %s (%d) in %s position.") % (_player, card.get_name(), card.attack, card.position.name.replace("_", " ")))
        else:
            utils.output(variables.LANGUAGE_HANDLER._("%s special summoning %s (%d/%d) in %s position.") % (_player, card.get_name(), card.attack, card.defense, card.position.name.replace("_", " ")))
    else:
        utils.output(variables.LANGUAGE_HANDLER._("%s summoning %s (%d/%d) in %s position.") % (_player, card.get_name(), card.attack, card.defense, card.position.name.replace("_", " ")))
