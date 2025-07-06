import io

from core import utils

@utils.duel_message_handler(93)
def msg_equip(client, data, data_length):
    data = io.BytesIO(data[1:])
    controller, location, sequence, position = client.read_location(data)
    target_controller, target_location, target_sequence, target_position = client.read_location(data)
    card = client.get_card(controller, location, sequence)
    target = client.get_card(target_controller, target_location, target_sequence)
    equip(client, card, target)

def equip(client, card, target):
    # todo: fix
    #utils.output(variables.LANGUAGE_HANDLER._("{card} equipped to {target}.").format(card=card.get_name(), target=target.get_name()))
    utils.output("Card equipped to target.")


