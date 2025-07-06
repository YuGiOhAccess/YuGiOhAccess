import sys
from pathlib import Path
import logging
import wx
from ui import fatal_exception_ui
from ui.app import YuGiOhAccessAPP
from ui.frame import YuGiOhAccessFrame
from core import variables
from core import utils
from game.language_handler import LanguageHandler
from core.exceptions import LanguageException


def main():
    app = YuGiOhAccessAPP()
    # attach exception hook
    fatal_exception_ui.attach_exception_hook()
    variables.LOCAL_DATA_DIR = variables.EXECUTABLE_DIR / "data"
    utils.setup()
    logger = logging.getLogger(__name__)
    logger.info("Starting YuGiOhAccess")
    utils.log_debug_info()
    utils.parse_dev_options()
    logger.info("Loading config")
    variables.config.load(Path(variables.APP_DATA_DIR) / "config.json")
    variables.config.save(Path(variables.APP_DATA_DIR) / "config.json")
    logger.info("Loading languages")
    variables.LANGUAGE_HANDLER = LanguageHandler()
    variables.LANGUAGE_HANDLER.add("english", "en")
    try:
        variables.LANGUAGE_HANDLER.set_primary_language("english")
    except LanguageException as e:
        logger.error("Failed to set primary language: "+str(e))
        sys.exit(1)
    frame = YuGiOhAccessFrame(None, wx.ID_ANY, "YuGiOhAccess")
    app.SetTopWindow(frame)
    logger.info("Showing frame")
    frame.Show()
    logger.info("Starting main loop")
    app.MainLoop()
    logger.info("Main loop ended, cleaning up")
    if variables.DISCORD_PRESENCE_MANAGER:
        variables.DISCORD_PRESENCE_MANAGER.stop()
        variables.DISCORD_PRESENCE_MANAGER.join()

SCRIPT="""
tell application "VoiceOver"                                                                                                         
    output ""                                                                                                                        
end tell                                                                                                                             
 """

if __name__ == '__main__':
    # so run this script until the permission error comes up.
    # basically only way to do this, is to run it in a loop with subprocess.Popen, and when it takes more than 2 seconds to respond, we know the permission dialog has been szhown.
    # then we can break out
    if sys.platform == "darwin":
        import subprocess
        import time
        while True:
            vo_process = subprocess.Popen(["osascript", "-e", SCRIPT])
            # if the process hasn't stopped after 2 second, then break out of the loop (permission dialog has been shown)
            time.sleep(2)
            if vo_process.poll() is None:
                break
    main()
 