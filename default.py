import font_installer
import playerprops
import sys
import threading
import time
import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

WINDOW_PROP = "TinyPPI.Running"
SKIN_PROP = "TinyPPI.Active"

DIALOG_LOCK = False


class TinyPPIDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = False
        self.monitor = xbmc.Monitor()
        self._opened_at = 0

    def onInit(self):
        self._running = True
        self._opened_at = time.time()

        playerprops.update_properties(self)
        self._start_update_loop()

    def _start_update_loop(self):
        t = threading.Thread(target=self._update_loop, daemon=True)
        t.start()

    def _update_loop(self):

        player = xbmc.Player()

        while self._running and not self.monitor.abortRequested():

            if not player.isPlaying():
                break

            if not xbmc.getCondVisibility("Window.IsActive(fullscreenvideo)"):
                break

            playerprops.update_properties(self)

            if self.monitor.waitForAbort(1):
                break

        self.close_dialog()

    def onClick(self, controlId):
        self.close_dialog()

    def onAction(self, action):

        if time.time() - self._opened_at < 0.3:
            return

        self.close_dialog()

    def close_dialog(self):
        self._running = False

        try:
            self.close()
        except:
            pass

    def onClosed(self):
        xbmcgui.Window(10000).clearProperty(WINDOW_PROP)
        xbmcgui.Window(10000).clearProperty(SKIN_PROP)


def open_tinyppi():

    global DIALOG_LOCK

    if DIALOG_LOCK:
        return

    player = xbmc.Player()

    if not xbmc.getCondVisibility("Window.IsActive(fullscreenvideo)"):
        xbmc.log("TinyPPI: not in fullscreen video", xbmc.LOGINFO)
        return

    if not player.isPlaying():
        xbmc.log("TinyPPI: nothing is playing", xbmc.LOGINFO)
        return

    if xbmcgui.Window(10000).getProperty(WINDOW_PROP) == "true":
        xbmc.log("TinyPPI already open", xbmc.LOGINFO)
        return

    xbmcgui.Window(10000).setProperty(WINDOW_PROP, "true")
    xbmcgui.Window(10000).setProperty(SKIN_PROP, "true")

    try:
        dialog = TinyPPIDialog(
            'script-tinyppi-main.xml',
            ADDON_PATH,
            'Default',
            '1080i'
        )

        dialog.doModal()
        del dialog

    finally:
        DIALOG_LOCK = True
        xbmc.Monitor().waitForAbort(0.3)
        DIALOG_LOCK = False

        xbmcgui.Window(10000).clearProperty(WINDOW_PROP)
        xbmcgui.Window(10000).clearProperty(SKIN_PROP)


if __name__ == '__main__':

    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if 'dialog' in args:
        import dialog
        dialog.open_dialog()
    else:
        open_tinyppi()
