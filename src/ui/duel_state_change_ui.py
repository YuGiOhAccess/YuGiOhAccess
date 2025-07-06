import logging
import wx

from core import utils

from game.edo import structs

from ui import server_ui

logger = logging.getLogger(__name__)

@utils.packet_handler(structs.ServerIdType.DUEL_START)
def handle_duel_start(client, packet_data, packet_length):
    utils.output("Duel Starting")
    utils.get_ui_stack().clear_ui_stack()
    utils.get_discord_presence_manager().update_presence(
        state="Duel Starting"
    )

@utils.packet_handler(structs.ServerIdType.DUEL_END)
def handle_duel_end(client, packet_data, packet_length):
    utils.output("Duel ended")
    utils.get_ui_stack().music_audio_manager.fade_out_all_audio()
    wx.CallLater(400, wx.GetApp().GetTopWindow().play_main_music)
    wx.CallLater(400, utils.get_ui_stack().clear_ui_stack)
    wx.CallLater(750, server_ui.server_selection_menu)

@utils.packet_handler(structs.ServerIdType.NEW_REPLAY)
def handle_new_replay(client, packet_data, packet_length):
    logger.debug("New Replay")
    logger.debug(packet_data)
    

@utils.packet_handler(structs.ServerIdType.REPLAY)
def handle_replay(client, packet_data, packet_length):
    logger.debug("Replay")
    logger.debug(packet_data)
