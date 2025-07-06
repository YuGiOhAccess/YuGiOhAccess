
import wx
from ui.base_ui import VerticalMenu, InputUI, StatusMessage
from core import variables
from core import utils

from ui import server_ui

@utils.ui_function
def first_ui_help_info(return_ui=None):
    if not return_ui:
        return_ui = first_ui
    menu = VerticalMenu("Welcome to YuGiOhAccess", False)
    menu.append_item("Welcome to YuGiOhAccess. This menu will contain quick information about the keys needed to move around. Use the up and down arrow keys to navigate the menu.")
    menu.append_item("In most screens, you can press F1 to get help information. This will give you information about the keys needed to move around in that specific screen.")
    menu.append_item("When encountering a text field, you can just start typing to enter text into that field. An example is provided below.")
    menu.append_item(wx.TextCtrl, label="Type something here")
    menu.append_item("When encountering a slider, use the left and right arrow keys to adjust the value of the slider. An example is provided below.")
    slider = menu.append_item(wx.Slider, label="This is a slider")
    slider.SetRange(0, 100)
    slider.SetValue(50)
    menu.append_item("The same goes for combo boxes. Use the left and right arrow keys to navigate the options. The  option will automatically be selected when you press enter. An example is provided below.")
    choice = menu.append_item(wx.Choice, label="This is a combo box", choices=["Option 1", "Option 2", "Option 3"])
    choice.SetSelection(1)
    menu.append_item("When encountering a checkbox, use the space bar to toggle the checkbox. An example is provided below.")
    menu.append_item(wx.CheckBox, label="This is a checkbox")
    menu.append_item("Lastly a little about the duel field")
    menu.append_item("When you are in a duel, the field is layed out in a grid, with your field being in the bottom half, and the opponent's field being in the top half. Use the arrow keys to navigate the field.")
    menu.append_item("Use space to read a card, and enter to open up the actions for that card.")
    menu.append_item("Use backspace to open tue duel menu, where you can perform actions like attacking, ending your turn, and more.")
    menu.append_item("Use escape to go back to the duel field from the action or duel menu.")
    menu.append_item("That's all for now. If you want to see this information again, you can find it in the help section of the main menu.", return_ui)
    menu.append_item("Press enter to continue", return_ui)
    menu.set_help_text("Hey it's jessica, the developer of the YuGiOhAccess client, you found this little message, or maybe you were told it was here. Anyway. Welcome to YuGiOhAccess. This menu will contain quick information about the keys needed to move around. Use the up and down arrow keys to navigate the menu.")
    return menu

@utils.ui_function
def first_ui():
    if variables.config.get("first_time_run"):
        variables.config.set("first_time_run", False)
        # since it's the players, first time, we will do like any other game, and take them to the settings menu
        first_ui_help_info()
        return
    main_menu_view()
    return

@utils.ui_function
def main_menu_view():
    if isinstance(variables.DEV_OPTIONS.server, int):
        server_ui.server_selection_menu()
        return
    current_nickname = variables.config.get("nickname")
    main_menu = VerticalMenu("Main Menu")
    main_menu.set_help_text("Main menu. Use the up and down arrow keys to navigate the menu, and press enter to select an option")
    main_menu.append_item(f"YuGiOh Access, {utils.version_string_to_pretty(variables.APP_VERSION)}", None)
    main_menu.append_item(f"Play ({current_nickname})", server_ui.server_selection_menu)
    main_menu.append_item("Settings", settings_menu)
    main_menu.append_item("Help", help_menu_view)
    if not variables.IS_FROZEN:
        main_menu.append_item("Make Windbot deck", make_windbot_deck)
        main_menu.append_item("Make deck string from Windbot deck", make_deck_string_from_windbot_deck)
    main_menu.append_item("Exit", wx.GetTopLevelWindows()[0].Close)
    utils.get_discord_presence_manager().update_presence(
        state="In the main menu",
        details="Getting ready to duel",
    )
    return main_menu

@utils.ui_function
def change_nickname(current_nickname):
    nickname_input = InputUI("Change nickname", default_value=current_nickname)
    new_nickname = nickname_input.show()
    if not new_nickname or new_nickname == current_nickname:
        utils.output("Nickname unchanged")
        return main_menu_view()
    variables.config.set("nickname", new_nickname)
    utils.output(f"Changed nickname to {new_nickname}")
    return main_menu_view()
@utils.ui_function
def settings_menu(return_to=None):
    if not return_to:
        return_to = main_menu_view
    settings_menu = VerticalMenu("Settings", False)
    music_volume_slider = settings_menu.append_item(wx.Slider, label="Music volume")
    music_volume_slider.SetRange(0, 20)
    current_music_volume = utils.get_ui_stack().music_audio_manager.get_volume() * 20
    current_music_volume = int(current_music_volume)
    music_volume_slider.SetValue(current_music_volume)
    music_volume_slider.Bind(wx.EVT_SLIDER, on_music_volume_change)
    music_volume_slider.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("Use the left and right arrow keys to adjust the music volume"))
    sound_effects_volume_slider = settings_menu.append_item(wx.Slider, label="Sound effects volume")
    sound_effects_volume_slider.SetRange(0, 20)
    current_sound_effects_volume = utils.get_ui_stack().sound_effects_audio_manager.get_volume() * 20
    current_sound_effects_volume = int(current_sound_effects_volume)
    sound_effects_volume_slider.SetValue(current_sound_effects_volume)
    sound_effects_volume_slider.Bind(wx.EVT_SLIDER, on_sound_effects_volume_change)
    sound_effects_volume_slider.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("Use the left and right arrow keys to adjust the sound effects volume"))
    # checkbox for providing tooltips
    hints_checkbox = settings_menu.append_item(wx.CheckBox, label="Enable hints")
    hints_checkbox.SetValue(variables.config.get("enable_hints"))
    hints_checkbox.Bind(wx.EVT_CHECKBOX, lambda event: variables.config.set("enable_hints", event.IsChecked()))
    hints_checkbox.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("When checked, hints like this will be spoken after a short delay. When unchecked, hints will not be spoken"))
    #checkbox for screenreader output only on application focus
    screenreader_output_checkbox = settings_menu.append_item(wx.CheckBox, label="Only output to screenreader when game window is focused")
    screenreader_output_checkbox.SetValue(variables.config.get("screenreader_output_only_on_application_focus"))
    screenreader_output_checkbox.Bind(wx.EVT_CHECKBOX, lambda event: variables.config.set("screenreader_output_only_on_application_focus", event.IsChecked()))
    screenreader_output_checkbox.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("When checked, the screenreader will only output text when the game window is focused. When unchecked, the screenreader will output text even if the window is in the background"))
    # checkbox for helper zones
    helper_zones_checkbox = settings_menu.append_item(wx.CheckBox, label="Enable helper zones")
    helper_zones_checkbox.SetValue(variables.config.get("helper_zones"))
    helper_zones_checkbox.Bind(wx.EVT_CHECKBOX, lambda event: variables.config.set("helper_zones", event.IsChecked()))
    helper_zones_checkbox.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("When checked, empty zones between and to the left and right of the extra monster zones will be shown. When unchecked, these zones will not be shown. Enabling this, might help in navigate the duel field better for newer players"))
    # rock paper scissors behavior for the bot
    # the options should be random (default), always show rock, always show paper, always show scissors
    rock_paper_scissors_behavior = settings_menu.append_item(wx.Choice, label="Rock paper scissors behavior for the bot", choices=["Random", "Always show rock", "Always show paper", "Always show scissors"])
    existing_rock_paper_scissors_bot_behavior = variables.config.get("rock_paper_scissors_bot_behavior")
    if existing_rock_paper_scissors_bot_behavior == "random":
        rock_paper_scissors_behavior.SetSelection(0)
    elif existing_rock_paper_scissors_bot_behavior == "rock":
        rock_paper_scissors_behavior.SetSelection(1)
    elif existing_rock_paper_scissors_bot_behavior == "paper":
        rock_paper_scissors_behavior.SetSelection(2)
    elif existing_rock_paper_scissors_bot_behavior == "scissors":
        rock_paper_scissors_behavior.SetSelection(3)
    rock_paper_scissors_behavior.Bind(wx.EVT_CHOICE, on_rock_paper_scissors_bot_behavior_change)
    rock_paper_scissors_behavior.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("Select the behavior of the bot in rock paper scissors. Random is the default, the bot will randomly pick rock, paper or scissors. Always show rock, paper or scissors will make the bot always pick that option"))
    # enable or disable bot chatter
    bot_chatter_checkbox = settings_menu.append_item(wx.CheckBox, label="Enable bot chatter during duels")
    bot_chatter_checkbox.SetValue(variables.config.get("enable_bot_chat"))
    bot_chatter_checkbox.Bind(wx.EVT_CHECKBOX, lambda event: variables.config.set("enable_bot_chat", event.IsChecked()))
    bot_chatter_checkbox.Bind(wx.EVT_SET_FOCUS, lambda event: utils.provide_tooltip("When checked, the bot will say things during duels. When unchecked, the bot will not say anything"))

    settings_menu.append_item("Done", return_to)
    return settings_menu


def on_music_volume_change(event):
    volume = event.GetEventObject().GetValue()
    adjusted_volume = volume * 5
    float_volume = adjusted_volume / 100
    utils.get_ui_stack().music_audio_manager.set_volume(float_volume)
    updated_volume_from_manager = utils.get_ui_stack().music_audio_manager.get_volume()
    variables.config.set("music_volume", updated_volume_from_manager)


def on_sound_effects_volume_change(event):
    volume = event.GetEventObject().GetValue()
    adjusted_volume = volume * 5
    float_volume = adjusted_volume / 100
    utils.get_ui_stack().sound_effects_audio_manager.set_volume(float_volume)
    utils.get_ui_stack().sound_effects_audio_manager.play_audio("click.wav")
    updated_volume_from_manager = utils.get_ui_stack().sound_effects_audio_manager.get_volume()
    variables.config.set("sound_effects_volume", updated_volume_from_manager)

def on_rock_paper_scissors_bot_behavior_change(event):
    choice = event.GetEventObject().GetCurrentSelection()
    if choice == 0:
        variables.config.set("rock_paper_scissors_bot_behavior", "random")
    elif choice == 1:
        variables.config.set("rock_paper_scissors_bot_behavior", "rock")
    elif choice == 2:
        variables.config.set("rock_paper_scissors_bot_behavior", "paper")
    elif choice == 3:
        variables.config.set("rock_paper_scissors_bot_behavior", "scissors")

from game.card.ydke import Deck # noqa

@utils.ui_function
def help_menu_view():
    help_menu = VerticalMenu("Help")
    help_menu.set_help_text("Help menu. Use the up and down arrow keys to navigate the menu, and press enter to select an option")
    help_menu.append_item("Help", None)
    help_menu.append_item("First time information", lambda: first_ui_help_info(help_menu_view))
    help_menu.append_item("Back to main menu", main_menu_view)
    return help_menu

@utils.ui_function
def make_windbot_deck():
    windbot_deck = VerticalMenu("Windbot deck")
    name = windbot_deck.append_item(wx.TextCtrl, label="Deck name")
    ydke_string = windbot_deck.append_item(wx.TextCtrl, label="Deck in YDKE format")
    windbot_deck.append_item("Done", lambda: save_windbot_deck(name.GetValue(), ydke_string.GetValue()))
    return windbot_deck

def save_windbot_deck(name, ydke_string):
        # if they are empty, go back to main menu
    if not name or not ydke_string:
        return main_menu_view()
    deck = Deck.from_ydke(ydke_string)
    # put it on the clipboard
    deck_data = deck.to_windbot_format()
    wx.TheClipboard.Open()
    wx.TheClipboard.SetData(wx.TextDataObject(deck_data))
    wx.TheClipboard.Close()
    sm = StatusMessage(f"Deck {name} has been saved to the clipboard", main_menu_view)
    sm.show()
    return
    
@utils.ui_function
def make_deck_string_from_windbot_deck():
    windbot_deck = VerticalMenu("Windbot deck")
    name = windbot_deck.append_item(wx.TextCtrl, label="Deck name")
    ydke_string = windbot_deck.append_item(wx.TextCtrl, label="Deck in Windbot format")
    windbot_deck.append_item("Done", lambda: save_deck_string_from_windbot_deck(name.GetValue(), ydke_string.GetValue()))
    return windbot_deck

def save_deck_string_from_windbot_deck(name, windbot_string):
    if not name or not windbot_string:
        return main_menu_view()
    deck = Deck.from_windbot_format(windbot_string)
    # put it on the clipboard
    deck_data = deck.to_ydke()
    wx.TheClipboard.Open()
    wx.TheClipboard.SetData(wx.TextDataObject(deck_data))
    wx.TheClipboard.Close()
    sm = StatusMessage(f"Deck {name} has been saved to the clipboard", main_menu_view)
    sm.show()
    return

