from core import utils
from core import variables

@utils.duel_message_handler(37)
def msg_reversedeck(client, data, data_length):
    utils.output(variables.LANGUAGE_HANDLER._("all decks are now reversed."))

