import io

from core import utils
from core import variables

@utils.duel_message_handler(101)
def msg_add_counter(client, data, data_length, action="add"):
    data = io.BytesIO(data[1:])
    counter_type = client.read_u16(data)
    player = client.read_u8(data)
    location = client.read_u8(data)
    sequence = client.read_u8(data)
    card = client.get_card(player, location, sequence)
    counter_amount = client.read_u16(data)
    update_counters(action, counter_type, counter_amount, card)

@utils.duel_message_handler(102)
def msg_remove_counter(client, data, data_length):
    return msg_add_counter(client, data, data_length, "remove")

def update_counters(action, counter_type, counter_amount, card):
    stype = variables.LANGUAGE_HANDLER.strings['counter'].get(counter_type, 'Counter %d' % counter_type)
    card_name = "Uknown card"
    if card:
        card_name = card.get_name()
    if action == "add":
        utils.output("%d %s added to %s" % (counter_amount, stype, card_name))
    else:
        utils.output("%d %s removed from %s" % (counter_amount, stype, card_name))
