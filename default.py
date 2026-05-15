import font_installer
import playerprops
import sys
import threading
import xbmc
import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

WINDOW_PROP = "TinyPPI.Running"
SKIN_PROP = "TinyPPI.Active"


class TinyPPIDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = False
        self.monitor = xbmc.Monitor()

    def onInit(self):
        self._running = True
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
        if controlId == 9000:
            self.close_dialog()

    def onAction(self, action):
        if action.getId() in (
            xbmcgui.ACTION_PREVIOUS_MENU,
            xbmcgui.ACTION_NAV_BACK,
            xbmcgui.ACTION_STOP,
        ):
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

    # set state
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
        xbmcgui.Window(10000).clearProperty(WINDOW_PROP)
        xbmcgui.Window(10000).clearProperty(SKIN_PROP)


if __name__ == '__main__':

    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if 'dialog' in args:
        import dialog
        dialog.open_dialog()
    else:
        open_tinyppi()
