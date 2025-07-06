import io
import time

import wx

from core import utils
from game.player import Player


from ui import duel_field

@utils.duel_message_handler(4)
def msg_start(client, data, data_len):
    # the first byte is the message id, so we skip it
    # the second byte is empty for this message
    data = io.BytesIO(data[2:])
    lp0 = client.read_u32(data)
    lp1 = client.read_u32(data)
    t0dz = client.read_u16(data)
    t0edz = client.read_u16(data)
    t1dz = client.read_u16(data)
    t1edz = client.read_u16(data)
    # start the duel
    start(client, lp0, lp1, t0dz, t0edz, t1dz, t1edz)

@utils.ui_function
def start(client, lp0, lp1, t0dz, t0edz, t1dz, t1edz):
    utils.get_ui_stack().music_audio_manager.fade_out_all_audio()
    time.sleep(0.050)
    # clear the ui stack
    utils.get_ui_stack().clear_ui_stack()
    field = duel_field.DuelField(client)
    client.set_duel_field(field)
    # lp is lifepoints
    # t0 and t1 are team 0 and 1
    # dz is deck size
    # edz is extra deck size
    utils.output(f"Starting lifepoints: {lp0} vs {lp1}")
    client.player = Player(lp0, lp1)
    utils.get_ui_stack().play_duel_sound_effect("start")
    # generate the duel field
    return field

