import io

from core import utils

from game.card import card_constants

@utils.duel_message_handler(33)
def msg_shuffle_hand(client, data, data_length):
    return msg_shuffle_others(client, data, card_constants.LOCATION.HAND)

@utils.duel_message_handler(39)
def msg_shuffle_extra_deck(client, data, data_length):
    return msg_shuffle_others(client, data, card_constants.LOCATION.EXTRA)

def msg_shuffle_others(client, data, location):
    data = io.BytesIO(data[1:])
    player = client.read_u8(data)
    count = client.read_u32(data)
    codes = []
    for i in range(count):
        codes.append(client.read_u32(data))
    shuffle_others(client, player, location, count, codes)
    return data.read()

def shuffle_others(client, player, location, count, codes):
    if location == card_constants.LOCATION.EXTRA or location == card_constants.LOCATION.DECK:
        utils.get_ui_stack().play_duel_sound_effect("shuffle")
    location = "hand" if location == card_constants.LOCATION.HAND else "extra deck"
    if player == client.what_player_am_i:
        utils.output(f"You shuffled {count} cards in your {location}.")
    else:
        utils.output(f"Opponent shuffled {count} cards in their {location}.")
