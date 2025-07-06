import io

from game.card.card import Card
from game.card import card_constants

from core import utils
from core import variables

@utils.duel_message_handler(42)
def msg_confirm_extra_decktop(client, data, data_length):
    cards = []
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    count = client.read_u32(data)
    for i in range(count):
        code = client.read_u32(data)
        if code & 0x80000000:
            code = code ^ 0x80000000 # don't know what this actually does
        card = Card(code)
        card.controller = client.read_u8(data)
        card.location = card_constants.LOCATION(client.read_u8(data))
        card.sequence = client.read_u32(data)
        cards.append(card)
    confirm_extra_decktop(client, player, cards)

def confirm_extra_decktop(client, player, cards):
    if player == client.what_player_am_i:
        utils.output(variables.LANGUAGE_HANDLER._("you reveal the following cards from your extra deck:"))
    else:
        utils.output(variables.LANGUAGE_HANDLER._("Your opponent reveals the following cards from their extra deck:"))
    for i, c in enumerate(cards):
        utils.output("%d: %s"%(i+1, c.get_name()))

