import logging
import threading
import concurrent.futures

import requests
import wx
from core import utils
from core import variables

from ui.base_ui import VerticalMenu
from ui import main_ui

logger = logging.getLogger(__name__)
RESULT_UI = main_ui.first_ui

@utils.ui_function
def ensure_yugioh_data_is_up_to_date():
    logger.info("Ensuring YuGiOh data is up to date")
    updater_menu = VerticalMenu("Loading data")
    updater_menu.append_item("Loading data, please wait...", None)
    threading.Thread(target=_update_data_thread, daemon=True).start()
    return updater_menu

def _update_data_thread():
    logger.info("Starting data update thread")
    all_has_executed = False  # Track overall success of updates
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(utils.update_data_repo, **repo): repo for repo in variables.DATA_REPOSITORIES}
        while not all_has_executed:
            wx.Yield()
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Failed to update: {e}")
                    results.append(False)
                    break
            if all(future.done() for future in futures):
                all_has_executed = True
                break
        if all(results):
            logger.info("All data updates successful")
            variables.LANGUAGE_HANDLER.connect_all_databases()
            wx.CallAfter(RESULT_UI)
        else:
            logger.error("Data update failed")
            wx.CallAfter(failed_data_update)

@utils.ui_function
def failed_data_update():
    logger.error("Data update failed")
    fail_menu = VerticalMenu("Data update failed")
    fail_menu.append_item("Data update failed. Please check your internet connection and try again.", None)
    fail_menu.append_item("Exit", wx.GetTopLevelWindows()[0].Close)
    return fail_menu
