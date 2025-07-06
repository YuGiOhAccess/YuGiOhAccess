import io
import threading
import time

from core import exceptions
from core import utils

from game.card import card_constants
from game.card.card import Card

@utils.duel_message_handler(90)
def msg_draw(client, data, length):
    data = io.BytesIO(data[1:])
    # print out the rest of the data
    player = client.read_u8(data)
    drawed = client.read_u32(data)
    cards = []
    for i in range(drawed):
        code = client.read_u32(data)
        position = client.read_u32(data)
        try:
            card = Card(code)
            card.set_location_and_position_info(player, card_constants.LOCATION.HAND, i, position)
            cards.append(card)
        except exceptions.CardNotFoundException:
            cards.append(None)
    draw(client, player, cards)

def draw(client, player, cards):
    _player = "You" if client.what_player_am_i == player else "Your opponent"
    utils.output(f"{_player} drew {len(cards)} cards")
    # if all of the cards are None
    if all(card is None for card in cards):
        return
    # if all cards are some form of face down, don't print them
    if all(not card.get_name()for card in cards):
        return
    threading.Thread(target=_play_draw_sound_effect, args=(len(cards),)).start()
    for x in range(len(cards)):
        if cards[x] is not None:
            print(cards[x].code)
            utils.output(f"{x+1}: {cards[x].get_name()}.")
        else:
            utils.output(f"{x}: face down.")

def _play_draw_sound_effect(amount):
    for i in range(amount):
        utils.get_ui_stack().play_random_duel_sound_effect_in_directory("draw")
        time.sleep(0.2)
