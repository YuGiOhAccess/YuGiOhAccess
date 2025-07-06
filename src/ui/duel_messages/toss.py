import io

from core import utils
from core import variables

@utils.duel_message_handler(130)
def msg_toss_coin(client, data, data_length, dice=False):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    count = client.read_u8(data)
    options = [client.read_u8(data) for i in range(count)]
    if dice:
        toss_dice(client, player, options)
    else:
        toss_coin(client, player, options)
    return data.read()

def toss_coin(client, player, options):
    s = variables.LANGUAGE_HANDLER.strings['system'][1623] + " "
    opts = [variables.LANGUAGE_HANDLER.strings['system'][60] if opt else variables.LANGUAGE_HANDLER.strings['system'][61] for opt in options]
    s += ", ".join(opts)
    utils.output(s)

def toss_dice(client, player, options):
    opts = [str(opt) for opt in options]
    s = variables.LANGUAGE_HANDLER.strings['system'][1624] + " "
    s += ", ".join(opts)
    utils.output(s)

@utils.duel_message_handler(131)
def msg_toss_dice(client, *args, **kwargs):
    kwargs['dice'] = True
    msg_toss_coin(*args, **kwargs)

