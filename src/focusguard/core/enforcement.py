LIMIT = 180
WARNING = 150


class Enforcer:
    def __init__(self, backend):
        self.backend = backend
        self.notify = None
        self.alreadyWarned = []

    def sendNotification(self, text):
        if self.notify is not None:
            self.notify("FocusGuard", text)

    def checkApp(self, window, appKind, secondsUsed, siteName=None):
        if appKind != "unproductive":
            return False

        appName = window.app_name
        if siteName is not None:
            appName = siteName
        if secondsUsed >= WARNING:
            if appName not in self.alreadyWarned:
                self.alreadyWarned.append(appName)
                self.sendNotification(appName + " is unproductive. It will close in " + str(LIMIT - secondsUsed) + " seconds.")

        if secondsUsed < LIMIT:
            return False

        self.sendNotification("Time's up! Closing " + appName + ".")
        if siteName is None:
            self.backend.close_app(window.pid)
        else:
            self.backend.close_tab(window)
        if appName in self.alreadyWarned:
            self.alreadyWarned.remove(appName)
        return True
