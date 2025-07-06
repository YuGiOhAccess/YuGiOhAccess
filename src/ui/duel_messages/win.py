import io
import logging

from core import utils
from core import variables

logger = logging.getLogger(__name__)

@utils.duel_message_handler(5)
def msg_win(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    reason = client.read_u8(data)
    win(client, player, reason)

def win(client, player, reason):
    logger.debug("Win: %d %d", player, reason)
    if player == 2:
        utils.output("You and your opponent ended the duel in a draw.")
        return

    def l_reason():
        return variables.LANGUAGE_HANDLER.strings['victory'][reason]

    if player == client.what_player_am_i:
        utils.output("You win the duel! %s" % l_reason())
    else:
        utils.output("You lose the duel! %s" % l_reason())

    # clear out stuff from the client
    client.duel_field = None
    client.player = None
    client.turn_count = 0
    client.has_announced_turn_order = False
    client.current_phase = ""
    client._what_player_am_i = -1
    client.is_it_my_turn = False
