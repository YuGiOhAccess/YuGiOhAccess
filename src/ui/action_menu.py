import logging
import struct

from ui.base_ui import VerticalMenu
from core import utils

from game.edo import structs
from game.card.card import Card

logger = logging.getLogger(__name__)

def show_action_menu_for_zone(client, zone):
    if not isinstance(zone.card, Card):
        return
    action_menu = VerticalMenu("Action Menu")
    action_menu.append_item(f"Actions for {zone.card.get_name()}")
    if zone.card in client.player.attackable:
        action_menu.append_item("Attack", function=lambda: send_attack(client, zone.card))
    activate_count = client.player.activatable.count(zone.card)
    if activate_count > 0:
        effect_descriptions = []
        for i in range(1, activate_count):
            description = zone.card.strings[i]
            effect_descriptions.append(description)
        ind = client.player.activatable[client.player.activatable.index(zone.card)].data
        description = zone.card.get_effect_description(ind)
        effect_descriptions.append(description)
        if activate_count == 1:
            action_menu.append_item(f"Activate effect: {effect_descriptions[0]}", function=lambda: send_activate(client, zone.card))
        else:
            for i in range(activate_count):
                action_menu.append_item(f"Activate effect {i+1}: {effect_descriptions[i]}", function=lambda i=i: send_activate(client, zone.card, i))
    if zone.card in client.player.special_summonable:
        action_menu.append_item("Special summon", function=lambda: send_special_summon(client, zone.card))
    if zone.card in client.player.summonable:
        action_menu.append_item("Summon", function=lambda: send_summon(client, zone.card))
    if zone.card in client.player.monster_settable:
        action_menu.append_item("Set", function=lambda: send_monster_set(client, zone.card))
    if zone.card in client.player.spell_settable:
        action_menu.append_item("Set", function=lambda: send_spell_set(client, zone.card))
    if zone.card in client.player.repositionable:
        action_menu.append_item("Reposition", function=lambda: send_reposition(client, zone.card))
    action_menu.append_item("Close", utils.get_ui_stack().pop_ui)
    utils.get_ui_stack().push_ui(action_menu)

def send_activate(client, card, addition=0):
    utils.get_ui_stack().pop_ui()
    logger.debug(f"Length of activatable: {len(client.player.activatable)}")
    logger.debug(f"Tried index: {client.player.activatable.index(card)}")
    logger.debug(f"Index after addition: {client.player.activatable.index(card) + addition}")
    index = client.player.activatable.index(card) + addition
    logger.debug(f"Activating effect {index}")
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (index << 16)+5))


def send_attack(client, card):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (client.player.attackable.index(card) << 16)+1))

def send_special_summon(client, card):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (client.player.special_summonable.index(card) << 16)+1))

def send_summon(client, card):
    # list all uis in the stack
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', client.player.summonable.index(card) << 16))

def send_monster_set(client, card):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (client.player.monster_settable.index(card) << 16) + 3))
        
def send_spell_set(client, card):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (client.player.spell_settable.index(card) << 16) + 4))

def send_reposition(client, card):
    utils.get_ui_stack().pop_ui()
    client.send(structs.ClientIdType.RESPONSE, struct.pack('I', (client.player.repositionable.index(card) << 16) + 2))
        