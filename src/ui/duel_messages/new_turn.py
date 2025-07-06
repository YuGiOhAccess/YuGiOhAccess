from core import utils

@utils.duel_message_handler(40)
def msg_new_turn(client, data, length):
    tp = int(data[1])
    new_turn(client, tp)

def new_turn(client, tp):
    utils.output(f"New turn for player {tp}.")
    client.turn_count += 1
    client.is_it_my_turn = tp == client.what_player_am_i
    client.player.clear_all()
    if client.is_it_my_turn:
        utils.get_ui_stack().play_duel_sound_effect("new_turn_me")
    else:
        utils.get_ui_stack().play_duel_sound_effect("new_turn_opponent")

