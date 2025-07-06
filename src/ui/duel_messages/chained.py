import io

from core import utils


@utils.duel_message_handler(71)
@utils.duel_message_handler(72)
@utils.duel_message_handler(73)
def msg_chained(client, data, data_length):
    data = io.BytesIO(data[1:])
    count = client.read_u8(data)
    # print the rest of the data if there is any
    print(data.read())
    chained(client, count)

@utils.duel_message_handler(74)
def msg_chain_end(client, data, data_length):
    return # it seems that this message is empty

@utils.duel_message_handler(75)
def msg_chain_negated(client, data, data_length):
    data = io.BytesIO(data[1:])
    count = client.read_u8(data)
    # print the rest of the data if there is any
    print(data.read())
    chain_negated(client, count)

@utils.duel_message_handler(76)
def msg_chain_disabled(client, data, data_length):
    data = io.BytesIO(data[1:])
    count = client.read_u8(data)
    # print the rest of the data if there is any
    print(data.read())
    chain_disabled(client, count)
    


def chained(client, count):
    print(f"Chained with {count} cards")

def chain_negated(client, count):
    print(f"Chain negated with {count} cards")

def chain_disabled(client, count):
    print(f"Chain disabled with {count} cards")