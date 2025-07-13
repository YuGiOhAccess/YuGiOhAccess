import ctypes
import logging

import wx

from ui import duel_state_change_ui # noqa
from ui import rock_paper_scissors_ui # noqa
from ui import room_ui # noqa
from ui import server_ui # noqa
from ui import main_ui # noqa
from ui import rematch_ui # noqa

from ui import duel_messages # noqa

# global handlers that don't fit in any other file
from core import utils

from game.edo import structs, structs_utils

logger = logging.getLogger(__name__)


@utils.packet_handler(structs.ServerIdType.CHAT_2)
def handle_chat_2(client, packet_data, packet_length):
    chat = structs.StocChat2.from_buffer_copy(packet_data)
    player_name = structs_utils.u16_to_string(chat.client_name)
    chat_message = structs_utils.u16_to_string(chat.msg)
    utils.output(f"{player_name}: {chat_message}")

@utils.packet_handler(structs.ServerIdType.ERROR_MSG)
def handle_error_msg(client, packet_data, packet_length):
    if packet_length == ctypes.sizeof(structs.ErrorMSG):
        m = structs.ErrorMSG.from_buffer_copy(packet_data)
        return handle_error(client, m)
    elif packet_length == ctypes.sizeof(structs.DeckErrrorMSG):
        m = structs.DeckErrrorMSG.from_buffer_copy(packet_data)
        return handle_deck_error(client, m)

def handle_error(client, message):
    if message.msg == 5:
        utils.output("Invalid version. Please update the game, or contact support if the issue persists.")
    
def handle_deck_error(client, message):
    logger.error(str(message))
    utils.output(str(message))

@utils.packet_handler(structs.ServerIdType.GAME_MSG)
def handle_game_msg(client, packet_data, packet_length):
    duel_message_id = int(packet_data[0])
    if duel_message_id not in utils.duel_message_handlers:
        logger.error(f"Unhandled duel message id: {duel_message_id}.\nPacket data:\n{packet_data}")
        return
    duel_message_handler = utils.duel_message_handlers[duel_message_id]
    logger.debug(f"Handling duel message id: {duel_message_id}, with handler: {duel_message_handler}")
    wx.CallAfter(duel_message_handler, client, packet_data, packet_length)
    