import io
from enum import IntFlag

from core import dotdict, exceptions
from core import utils

from game.card.card import Card
from game.card.location_conversion import LocationConversion
from game.card import card_constants

@utils.duel_message_handler(50)
def msg_move(client, data, data_length):
    data = io.BytesIO(data[1:])
    code = client.read_u32(data)
    old_controller, old_location, old_sequence, old_position = client.read_location(data)
    new_controller, new_location, new_sequence, new_position = client.read_location(data)
    reason = card_constants.REASON(client.read_u32(data))
    move(client, code, old_controller, old_location, old_sequence, old_position, new_controller, new_location, new_sequence, new_position, reason)

def move(client, code, old_controller, old_location, old_sequence, old_position, new_controller, new_location, new_sequence, new_position, reason):
    print(f"Move: {code}, {old_controller}, {old_location}, {old_sequence}, {old_position}, {new_controller}, {new_location}, {new_sequence}, {new_position}, {reason}")
    try:
        card = Card(code)
    except exceptions.CardNotFoundException:
        return
    card.set_location_and_position_info(old_controller, old_location, old_sequence, old_position)
    cnew = Card(code)
    cnew.set_location_and_position_info(new_controller, new_location, new_sequence, new_position)
    print(f"{card.name} moved from {old_location} to {new_location} because of {reason}")
    # remove the card from the old location
    client.get_duel_field().remove_card(card)
    if new_location == card_constants.LOCATION.GRAVE:
        if new_controller == client.what_player_am_i:
            client.get_duel_field().append_card_to_player_graveyard(cnew)
        else:
            fake_query = dotdict.DotDict()
            fake_query.controller = new_controller
            fake_query.location = new_location
            fake_query.sequence = new_sequence
            fake_query.position = new_position
            client.get_duel_field().append_card_to_opponent_graveyard(cnew, fake_query)
    elif new_location == card_constants.LOCATION.REMOVED:
        if new_controller == client.what_player_am_i:
            client.get_duel_field().append_card_to_player_banished(cnew)
        else:
            fake_query = dotdict.DotDict()
            fake_query.controller = new_controller
            fake_query.location = new_location
            fake_query.sequence = new_sequence
            fake_query.position = new_position
            client.get_duel_field().append_card_to_opponent_banished(cnew, fake_query)
    message = get_message_to_announce(client, card, cnew, reason)
    if message:
        utils.output(message)
    else:
        print("No message to announce")
        # print the information here
        print(f"{card.name} moved from {old_location} to {new_location} because of {reason}")


class Message(IntFlag):
    ME = 0x1
    OPPONENT = 0x2

def get_message_to_announce(client, card, cnew, reason):
    old_location_information = LocationConversion.from_card_location(client, card)  # noqa: F841
    new_card_information = LocationConversion.from_card_location(client, cnew)
    if reason & card_constants.REASON.DESTROY and card.location != cnew.location:
        utils.get_ui_stack().play_duel_sound_effect("destroy")
        return resolve_message(client, card, cnew,
                               {Message.ME: "Your card %s destroyed.",
                                Message.OPPONENT: "Your opponent's card %s destroyed."},
                                card.get_name()
                                )
    elif card.location == cnew.location and card.location & card_constants.LOCATION.ONFIELD:
        if card.controller != cnew.controller:
            utils.get_ui_stack().play_duel_sound_effect("swapcontrol")
            return resolve_message(client, card, cnew,
                                   {Message.ME: "Your card %s switched control to your opponent, and is now located at %s.",
                                    Message.OPPONENT: "Your opponent's card %s switched control to you, and is now located at %s."},
                                    card.get_name(), new_card_information.to_human_readable()
                                    )
        else:
            # only column changed
            return resolve_message(client, card, cnew,
                                   {Message.ME: "Your card %s changed column to %s.",
                                    Message.OPPONENT: "Your opponent's card %s changed column to %s."},
                                    card.get_name(), new_card_information.to_human_readable()
                                    )
    elif reason & card_constants.REASON.DISCARD and card.location != cnew.location:
        utils.get_ui_stack().play_duel_sound_effect("discard")
        return resolve_message(client, card, cnew,
    {Message.ME: "You discarded %s.",
    Message.OPPONENT: "Your opponent discarded %s."},
    card.get_name()
    )
    elif card.location == card_constants.LOCATION.REMOVED and cnew.location & card_constants.LOCATION.ONFIELD:
        return resolve_message(client, card, cnew,
    {Message.ME: "your banished card %s returns to the field at %s.",
    Message.OPPONENT: "Your opponent's banished card %s returns to the field at %s."},
    card.get_name(), new_card_information.to_human_readable()
    )
    elif card.location == card_constants.LOCATION.GRAVE and cnew.location & card_constants.LOCATION.ONFIELD:
        return resolve_message(client, card, cnew,
    {Message.ME: "Your card %s returns from the graveyard to the field at %s.",
    Message.OPPONENT: "Your opponent's card %s returns from the graveyard to the field at %s."},
    card.get_name(), new_card_information.to_human_readable()
    )
    elif cnew.location == card_constants.LOCATION.HAND and card.location != cnew.location:
        utils.get_ui_stack().play_duel_sound_effect("return")
        return resolve_message(client, card, cnew,
    {Message.ME: "%s returned to your hand.",
    Message.OPPONENT: "%s returned to your opponent's hand."},
    card.get_name()
    )
    elif reason & (card_constants.REASON.RELEASE | card_constants.REASON.SUMMON) and card.location != cnew.location:
        utils.get_ui_stack().play_duel_sound_effect("tribute")
        return resolve_message(client, card, cnew,
    {Message.ME: "You tributte %s.",
    Message.OPPONENT: "Your opponent tributtes %s."},
    card.get_name()
    )
    elif card.location == card_constants.LOCATION.OVERLAY | card_constants.LOCATION.MONSTER_ZONE and cnew.location & card_constants.LOCATION.GRAVE:
        utils.get_ui_stack().play_duel_sound_effect("detach")
        return resolve_message(client, card, cnew,
    {Message.ME: "You used overlay unit %s.",
    Message.OPPONENT: "Your opponent used overlay unit %s."},
    card.get_name()
    )
    elif card.location != cnew.location and cnew.location == card_constants.LOCATION.GRAVE:
        utils.get_ui_stack().play_duel_sound_effect("sendtograve")
        return resolve_message(client, card, cnew,
    {Message.ME: "Your %s was sent to the graveyard.",
    Message.OPPONENT: "Your opponent's %s was sent to the graveyard."},
    card.get_name()
    )
    elif card.location != cnew.location and cnew.location == card_constants.LOCATION.REMOVED:
        return resolve_message(client, card, cnew,
    {Message.ME: "Your %s was banished.",
    Message.OPPONENT: "Your opponent's %s was banished."},
    card.get_name()
    )
    elif card.location != cnew.location and cnew.location == card_constants.LOCATION.DECK:
        utils.get_ui_stack().play_duel_sound_effect("sendtodeck")
        return resolve_message(client, card, cnew,
    {Message.ME: "Your %s returned to your deck.",
    Message.OPPONENT: "Your opponent's %s returned to their deck."},
    card.get_name()
    )
    elif card.location != cnew.location and cnew.location == card_constants.LOCATION.EXTRA:
        utils.get_ui_stack().play_duel_sound_effect("sendtoextradeck")
        return resolve_message(client, card, cnew,
    {Message.ME: "Your %s returned to your extra deck.",
    Message.OPPONENT: "Your opponent's %s returned to their extra deck."},
    card.get_name()
    )
    elif card.location == card_constants.LOCATION.DECK and cnew.location == card_constants.LOCATION.SPELL_AND_TRAP_ZONE and cnew.position != card_constants.POSITION.FACE_DOWN:
        return resolve_message(client, card, cnew,
    {Message.ME: "You activate %s from your deck.",
    Message.OPPONENT: "Your opponent activates %s from their deck."},
    card.get_name()
    )
    elif cnew.location == (card_constants.LOCATION.OVERLAY | card_constants.LOCATION.MONSTER_ZONE):
        attached_to = client.get_card(cnew.controller, cnew.location ^ card_constants.LOCATION.OVERLAY, cnew.sequence)
        return resolve_message(client, card, cnew,
    {Message.ME: "your card %s was attached to %s as XYZ material.",
    Message.OPPONENT: "Your opponent's card %s was attached to %s as XYZ material."},
    card.get_name(), attached_to.get_name()
    )



def resolve_message(client, old_card, new_card, messages, *args):
    if old_card.controller == client.what_player_am_i:
        return messages[Message.ME] % args if len(args) > 1 else messages[Message.ME] % args[0]
    else:
        return messages[Message.OPPONENT] % args if len(args) > 1 else messages[Message.OPPONENT] % args[0]
