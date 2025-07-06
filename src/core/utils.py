import argparse
import os
import json
import sys
import zipfile
import logging
import time
import shutil
from pathlib import Path
import re
from functools import wraps

import requests
import urllib
import velopack
import wx

from core import discord_presence
from core import variables

def setup_logging():
    # set up the logging
    # we just want the message, followed by the level
    # make sure the logs directory is there, gotten from the variables.LOG_FILE
    log_dir = variables.LOG_FILE.parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    # go through all the files in the logs directory and if they are older than 14 days, delete them
    for file in log_dir.iterdir():
        if file.is_file() and file.stat().st_mtime < (time.time() - 1209600):
            file.unlink()
    # we want 2 handlers, 1 for the file, 1 for the console
    # set up the file handler
    file_handler = logging.FileHandler(variables.LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(message)s - %(levelname)s"))
    # set up the console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter("%(message)s - %(levelname)s"))
    # set up the logger
    logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
    # requests and urllib3 are too verbose, so we want to set them to warning
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def run_velopack():
    logger = logging.getLogger(__name__)
    logger.info("Running Velopack application")
    velopack.App().run()
    update_manager = None
    url = None
    try:
        logger.debug("Fetching the latest version URL from GitHub")
        response = urllib.request.urlopen("https://github.com/YuGiOhAccess/YuGiOhAccess/releases/latest/")
        version_url_frags = response.url.split("/")
        version = version_url_frags[-1]
        url = f"https://github.com/YuGiOhAccess/YuGiOhAccess/releases/download/{version}/"
        logger.info(f"Latest version URL: {url}")
    except urllib.error.HTTPError:
        logger.error("Failed to get the latest version URL from GitHub")
        return

    try:
        logger.info("Initializing UpdateManager")
        update_manager = velopack.UpdateManager(url)
    except Exception as e:
        logger.error(f"Failed to initialize UpdateManager: {e}")
    return
    update_info = update_manager.check_for_updates()
    if not update_info:
        logger.info("No updates available")
        return
    try:
        logger.info(f"Updates available: {update_info}")
        update_manager.download_updates(update_info)
        logger.info("Updates downloaded successfully")
    except Exception as e:
        logger.error(f"Failed to download updates: {e}")
        return
    try:
        logger.info("Applying updates")
        update_manager.apply_updates_and_restart(update_info)
    except Exception as e:
        logger.error(f"Failed to apply updates: {e}")
        return



def setup():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Setting up")
    # set up the data directory
    logger.info("Setting up data directory")
    data_dir = Path(variables.APP_DATA_DIR)
    if not data_dir.exists():
        logger.info("Creating data directory")
        data_dir.mkdir(parents=True, exist_ok=True)
    else:
        logger.info("Data directory exists")
        # done
        logger.info("Setup complete")
        run_velopack()


def log_debug_info():
    logger = logging.getLogger(__name__)
    logger.debug(f"variables.EXECUTABLE_DIR: {variables.EXECUTABLE_DIR}")
    logger.debug(f"variables.APP_DATA_DIR: {variables.APP_DATA_DIR}")
    # if we are frozen, use sys._MEIPASS
    if getattr(sys, 'frozen', False):
        logger.debug("Running in a PyInstaller bundle")
        logger.debug(f"sys._MEIPASS: {sys._MEIPASS}")

def parse_dev_options():
    parser = argparse.ArgumentParser("YuGiOhAccess", add_help=False)
    # override the help option
    parser.add_argument('-h', '--help', action='store_true', dest='help')
    # add an option for whih server to auto connect to, based on the server list, it's a number
    parser.add_argument("--server", type=int, help="Automatically connect to a server")
    # make an option, called action, that can either be create or join. If server is defined, this is required. If server is not defined, this cannot be used.
    parser.add_argument("--action", choices=["create", "join"], help="Create or join a duel")
    # add an option for the duel id, if action is join, this is required
    parser.add_argument("--id", type=int, help="The duel id to join")
    # add an option for password, this is optional if action is join, but required if action is create
    parser.add_argument("--password", help="The password for the duel")
    # deck is optional, if it's defined, it will try to load the deck from the decks directory
    parser.add_argument("--deck", help="The deck to use")
    # add a bot option, if this is defined, it will add a bot to the duel, if this is not specified, default is false and bot will not be added
    parser.add_argument("--bot", action="store_true", help="Add a bot to the duel")
    # botdeck is optional, if it's defined, it will tell the bot to use that deck. If it's not found, the bot will use a random deck
    parser.add_argument("--botdeck", help="The deck for the bot to use")
    # add a shuffle option, if this is not specified, the default should be true, if this is set to false, decks wont be shuffled
    parser.add_argument("--no-shuffle", action="store_true", help="Don't shuffle the decks")
    # add a draw option, this is an int, if specified, controlls how many cards to draw at the start of the duel
    parser.add_argument("--draw", type=int, help="How many cards to draw at the start of the duel")

    # parse the arguments
    if variables.IS_FROZEN:
        # pass an empty list if we are frozen, as to disable the command line arguments
        variables.DEV_OPTIONS = parser.parse_args([])
    else:
        variables.DEV_OPTIONS = parser.parse_args()
    # if help is true, print the help and exit
    if variables.DEV_OPTIONS.help:
        parser.print_help()
        sys.exit(0)
    # validate the options
    validate_dev_options(parser)
    
def validate_dev_options(parser):
    if variables.DEV_OPTIONS.server:
        if not variables.DEV_OPTIONS.action:
            parser.error("--server requires --action")
        if variables.DEV_OPTIONS.action == "join" and not variables.DEV_OPTIONS.id:
            parser.error("--action join requires --id")
        if variables.DEV_OPTIONS.action == "create" and not variables.DEV_OPTIONS.password:
            parser.error("--action create requires --password")

# me being the caller (we don't want to address me)
def guess_items_in(items, name, me):
    name = name.lower()
    me = me.lower()
    found_items = []
    for item in items:
        if item.lower() == name:
            return [item] # exact match
        if item.lower() == me:
            continue # don't address me
        if item.lower().startswith(name):
            found_items.append(item)
    found_items.sort()
    return found_items

def extract_trailing_numbers(input_string):
    # Use regular expression to find trailing digits
    match = re.search(r'\d+$', input_string)
    if match:
        return int(match.group())  # Convert the matched digits to an integer
    else:
        return None  # Return None if no trailing digits are found
    
def get_ui_stack():
    return wx.GetTopLevelWindows()[0]

_LAST_UI_FUNCTION = None
def get_last_ui_function():
    return _LAST_UI_FUNCTION

# Make an ui decorator that first pups the last, then runs the function, then pushes the returned value
def ui_function(func):
    global _LAST_UI_FUNCTION
    _LAST_UI_FUNCTION = func
    @wraps(func)
    def wrapper(*args, **kwargs):
        wx.GetTopLevelWindows()[0].pop_ui()
        result = func(*args, **kwargs)
        if not result:
            return wrapper
        wx.GetTopLevelWindows()[0].push_ui(result)
    return wrapper

def get_discord_presence_manager():
    if not variables.DISCORD_PRESENCE_MANAGER:
        variables.DISCORD_PRESENCE_MANAGER = discord_presence.DiscordPresenceManager(client_id=variables.DISCORD_APPLICATION_INFO.client_id)
        variables.DISCORD_PRESENCE_MANAGER.start()
    return variables.DISCORD_PRESENCE_MANAGER

packet_handlers = {}

def packet_handler(packet_id):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # get the on_error handler, id -1
                handler = packet_handlers.get(-1)
                if handler:
                    handler(e, packet_id, func, *args, **kwargs)
                else:
                    raise e
        packet_handlers[packet_id] = wrapper
        return wrapper
    return decorator

duel_message_handlers = {}

def duel_message_handler(duel_message_id):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # get the on_error handler, id -1
                handler = duel_message_handlers.get(-1)
                if handler:
                    handler(e, duel_message_id, func, *args, **kwargs)
                else:
                    raise e
        duel_message_handlers[duel_message_id] = wrapper
        return wrapper
    return decorator




def get_main_menu_function():
    return get_ui_stack().get_main_ui()

# we want a function that can refresh the current ui
def refresh_ui():
    get_ui_stack().refresh_ui()

def output(message, interrupt=False):
    if wx.GetApp().IsActive():
        wx.GetTopLevelWindows()[0].output(message, interrupt)

def provide_tooltip(tooltip):
    if variables.config.get("enable_hints"):
        wx.CallLater(250, output, tooltip)

def _repo_not_valid(local_path):
    # if the local path doesn't exist, we should download it
    if not local_path.exists():
        return True
    # if the local path is not a directory, we should download it
    if not local_path.is_dir():
        return True
    # if the local path is empty, we should download it
    if not os.listdir(local_path):
        return True

def _should_redownload_repo(url, local_path):
    logger = logging.getLogger(__name__)
    if _repo_not_valid(local_path):
        # repo either dont exist, is not a directory or is empty
        logger.debug(f"Local path {local_path} is not valid, should download")
        # create the dir
        local_path.mkdir(parents=True, exist_ok=True)
    last_downloaded_file = local_path / "last_downloaded.txt"
    last_downloaded_date = ""
    if last_downloaded_file.exists():
        last_downloaded_date = last_downloaded_file.read_text()
    github_api_url = f"https://api.github.com/repos/{url}"
    # get the "updated_at" date from the github api
    response = requests.get(github_api_url)
    response.raise_for_status()
    response = response.json()
    updated_at = response["updated_at"]
    # if the updated_at is newer than the last_downloaded, we should download it
    if updated_at != last_downloaded_date:
        logger.debug(f"Local path {local_path} has an outdated version, should download. Old version: {last_downloaded_date}, new version: {updated_at}")
        return True, updated_at
    # if we got here, we should not download it
    logger.debug(f"Local path {local_path} is up to date, should not download")
    return False, None

def _download_repo(url, local_path, updated_at):
    logger = logging.getLogger(__name__)
    logger.debug(f"Downloading {url} to {local_path}")
    # create the local path
    local_path.mkdir(parents=True, exist_ok=True)
    # if the content folder exists, rename it to content.old
    local_content_path = local_path / "content"
    if local_content_path.exists():
        os.rename(local_content_path, local_path / "content.old")
    # get the zip file
    zip_file_url = f"https://github.com/{url}/archive/refs/heads/master.zip"
    local_zip_file = local_path / "master.zip"
    local_content_path = local_path / "content"
    with requests.get(zip_file_url, stream=True) as r:
        r.raise_for_status()
        with open(local_zip_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    # extract the zip file
    logger.debug(f"Extracting {local_zip_file} to {local_path}")
    old_content_of_local_path = list(local_path.iterdir())
    with zipfile.ZipFile(local_zip_file, "r") as zip_ref:
        zip_ref.extractall(local_path)
    logger.debug(f"Extracted {local_zip_file} to {local_path}")
    new_content_of_local_path = list(local_path.iterdir())
    # there should be 1 new folder, that is the content
    # rename that folder to content
    for item in new_content_of_local_path:
        if item.is_dir() and item.name not in old_content_of_local_path:
            os.rename(item, local_content_path)
            break
    # delete the zip file
    os.remove(local_zip_file)
    # delete the old content folder
    shutil.rmtree(local_path / "content.old", ignore_errors=True)
    (local_path / "last_downloaded.txt").write_text(updated_at)

def update_data_repo(name, url, local_path):
    logger = logging.getLogger(__name__)
    logger.debug(f"Updating {name} from {url} to {local_path}")
    try:
        redownload, updated_at = _should_redownload_repo(url, local_path)
        if redownload:
            _download_repo(url, local_path, updated_at)
        return True
    except Exception as e:
        logger.error(f"Failed to update {name}: {e}")
        return False

def version_string_to_pretty(version_string):
    # replace a with alpha, b with beta, rc with release candidate
    version_string = version_string.replace("a", " alpha ").replace("b", " beta ").replace("rc", " release candidate ")
    return version_string

def sanitize_filename(filename: str) -> str:
    """
    Remove or replace characters that are not valid in most operating systems' filenames.
    This version:
      - Removes leading/trailing whitespace.
      - Replaces invalid chars with '_'.
      - Collapses multiple underscores.
    """
    # Trim whitespace
    filename = filename.strip()
    
    # Replace invalid characters (anything not letters, digits, dots, hyphens, or underscores)
    # with an underscore.
    # You might also choose to remove them instead (re.sub(..., '') instead of '_')
    sanitized = re.sub(r'[^A-Za-z0-9_.-]+', '_', filename)
    
    # Optionally, you can collapse consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    
    # You might also want to handle cases where the filename is empty
    # or if it starts with a dot, etc.
    if not sanitized:
        sanitized = "_"
    
    return sanitized