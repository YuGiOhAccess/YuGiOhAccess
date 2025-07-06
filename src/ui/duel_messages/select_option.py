import logging
import io
import struct

from game.card.card import Card
from game.edo import structs

from ui.base_ui import VerticalMenu

from core import utils
from core import variables

logger = logging.getLogger(__name__)

@utils.duel_message_handler(14)
def msg_select_option(client, data, data_length):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    size = client.read_u8(data)
    options = []
    for i in range(size):
        options.append(client.read_u64(data))
    select_option(client, player, options)
    return data.read()

def select_option(client, player, options):
    logger.debug("Selecting option")
    logger.debug(f"Player id: {player}")
    logger.debug(f"Options: {options}")
    card = None
    opts = []
    for opt in options:
        code = opt >> 20
        stringid = opt & 0xfffff
        if code == 0:
            string = variables.LANGUAGE_HANDLER.strings['system'].get(stringid, variables.LANGUAGE_HANDLER._("Unknown option %d" % stringid))
            opts.append(string)
        else:
            card = Card(code)
            string = card.strings[stringid]
            opts.append(string)
    menu = VerticalMenu(variables.LANGUAGE_HANDLER._("Select option:"))
    if not card:
        menu.append_item("Select option")
    else:
        menu.append_item(f"Select option for {card.get_name()}")
    for idx, opt in enumerate(opts):
        menu.append_item(opt, function=lambda idx=idx: select(client, options, idx))
    utils.get_ui_stack().push_ui(menu)

def select(client, options, idx):
    print(f"Selecting option {idx}")
    print(options)
    opt = options[idx]
    code = opt >> 20
    stringid = opt & 0xfffff
    utils.get_ui_stack().pop_ui()
    if code == 0:
        string = variables.LANGUAGE_HANDLER.strings['system'].get(stringid, variables.LANGUAGE_HANDLER._("Unknown option %d" % stringid))
    else:
        card = Card(code)
        string = card.strings[stringid]
    utils.output(f"Selected option {string}")
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', idx))

