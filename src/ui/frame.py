from pathlib import Path
import logging
import random

from ui import data_updater_ui
import wx
import wx.adv

from ui import output
from ui import main_ui
from core import utils
from core import variables
from ui.audio import AudioManager

logger = logging.getLogger(__name__)

class YuGiOhAccessFrame(wx.Frame):
    def __init__(self, parent=None, id=-1, title="YuGiOhAccess"):
        logger.info("Initializing screenreader output")
        self.sr_output = output.output

        # init audio output
        logger.info("Initializing audio output")
        self.sound_effects_audio_manager = AudioManager("sound_effects_volume")
        self.music_audio_manager = AudioManager("music_volume")

        logger.info("Initializing frame")
        wx.Frame.__init__(self, parent, id, title)

        self.menubar = wx.MenuBar()
        self.file_menu = wx.Menu()
        self.about_menu_item = self.file_menu.Append(wx.ID_ABOUT, "&About", "Information about this program")
        self.Bind(wx.EVT_MENU, self.on_about, self.about_menu_item)
        self.exit_menu_item = self.file_menu.Append(wx.ID_EXIT, "E&xit", "Terminate the program")
        self.Bind(wx.EVT_MENU, self.on_exit, self.exit_menu_item)
        self.menubar.Append(self.file_menu, "&File")
        self.SetMenuBar(self.menubar)
 
        self.game_area = wx.Panel(self, name="Game Area")

        self.ui_stack = []

        # make a sizer for the game area and the input/output sizer, where the game area is to the left of the input/output sizer, and takes up 2/3 of the space
        self.main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.main_sizer.Add(self.game_area, 1, wx.EXPAND)

        self.SetSizer(self.main_sizer)

        # make the panel take up the whole window
        self.game_area.Fit()

        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_CLOSE, self.on_close)


        # max size of the window
        self.Maximize(True)
        # show
        self.Show(True)
        self.play_main_music()

        data_updater_ui.ensure_yugioh_data_is_up_to_date()
        self.ui_stack[-1].SetFocus()


    def push_ui(self, ui):
        logger.info(f"Pushing ui {ui}")
        logger.debug(f"Current ui stack: {self.prettify_ui_stack()}")
        self.ui_stack.append(ui)
        # update the self.game_area in the sizer to be this panel instead
        self.main_sizer.Add(ui, 2, wx.EXPAND)
        ui.Show()
        ui.SetFocus()
        self.Fit()

    def pop_ui(self):
        if len(self.ui_stack) == 0:
            return
        old_ui= self.ui_stack.pop()
        # remove from size
        if old_ui:
            self.main_sizer.Hide(old_ui)
            old_ui.Hide()
            old_ui.Close()
        # if there are still ui elements in the stack, set focus to the last one
        if len(self.ui_stack) > 0:
            self.ui_stack[-1].SetFocus()
        self.Layout()
        self.Fit()

    def clear_ui_stack(self):
        while len(self.ui_stack) > 0:
            self.pop_ui()

    def refresh_ui(self, ui_function):
        logger.info("Refreshing ui")
        logger.debug(f"Current ui stack: {self.prettify_ui_stack()}")
        self.pop_ui()
        ui_function()

    def get_main_ui(self):
        return  main_ui.main_menu_view()
    
    def prettify_ui_stack(self):
        return [str(ui) for ui in self.ui_stack]



    def on_about(self, event):
        # make an about dialog
        info = wx.adv.AboutDialogInfo()
        info.SetName("YuGiOhAccess (YuGiOhAccess)")
        info.SetVersion(utils.version_string_to_pretty(variables.APP_VERSION))
        info.SetDescription("An accessible client for playing Yu-Gi-Oh! online")
        info.SetDevelopers(["Jessica Tegner", "YuGiOhAccess contributors"])
        info.SetWebSite("https://YuGiOhAccess.com", "YuGiOhAccess Website")
        info.SetCopyright("Copyright (c) 2024 YuGiOhAccess")
        # write the long version of the gpl3 license in info.SetLicence
        info.SetLicence("""GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
                        
                        YuGiOhAccess is free software: you can redistribute it and/or modify
                        it under the terms of the GNU General Public License as published by
                        the Free Software Foundation, either version 3 of the License, or
                        (at your option) any later version.
                        """)
        wx.adv.AboutBox(info)

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        logger.info("Closing frame")
        if self.sound_effects_audio_manager:
            self.sound_effects_audio_manager.stop_all_audio()
        if self.music_audio_manager:
            self.music_audio_manager.stop_all_audio()
        event.Skip()

    def play_random_duel_sound_effect_in_directory(self, directory_name, x=0.0, y=0.0, z=0.0):
        # pick a random file from the data/sounds/duel/directory_name folder and play it
        sound_files = list(Path(variables.LOCAL_DATA_DIR / "sounds" / "duel" / directory_name).iterdir())
        # remove any that doesn't end with .flac, .wav,, .ogg or .opus
        sound_files = [file for file in sound_files if file.suffix in {".flac", ".wav", ".ogg", ".opus"}]
        random_sound_file = random.choice(sound_files)
        # keep in mind that the file is in duel/directory_name/random_sound_file.name
        self.sound_effects_audio_manager.play_audio(f"duel/{directory_name}/{random_sound_file.name}", x=x, y=y, z=z) 

    def play_duel_sound_effect(self, effect, x=0.0, y=0.0, z=0.0):
        # so the full path to the specific sound effect is sounds/duel/effect, .flac, .wav, .ogg or .opus
        resolved_file_path = None
        for extension in {".flac", ".wav", ".ogg", ".opus"}:
            file_path = Path(variables.LOCAL_DATA_DIR / "sounds" / "duel" / f"{effect}{extension}")
            if file_path.exists():
                resolved_file_path = file_path
                break
        if not resolved_file_path:
            logger.warn(f"Sound effect {effect} not found. Tried with extensions {'.flac', '.wav', '.ogg', '.opus'}")
            return
        self.sound_effects_audio_manager.play_audio(f"duel/{effect}{resolved_file_path.suffix}", x=x, y=y, z=z)

    def play_main_music(self):
        # pick a random file from the data/sounds/music/start folder and play it
        music_files = list(Path(variables.LOCAL_DATA_DIR / "sounds" / "music" / "start").iterdir())
        random_music_file = random.choice(music_files)
        # keep in mind that the file is in music/start/random_music_file.name
        self.music_audio_manager.play_audio(f"music/start/{random_music_file.name}", looping=True)

    def output(self, text, interrupt=False):
        self.sr_output.output(text, interrupt) # Assume this is some function for outputting text



    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        # f5 and f6 are used for sound effect volume
        # f7 and f8 are used for music volume
        if keycode == wx.WXK_F5:
            self.sound_effects_audio_manager.decrease_volume()
        elif keycode == wx.WXK_F6:
            self.sound_effects_audio_manager.increase_volume()
        elif keycode == wx.WXK_F7:
            self.music_audio_manager.decrease_volume()
        elif keycode == wx.WXK_F8:
            self.music_audio_manager.increase_volume()
        event.Skip()
