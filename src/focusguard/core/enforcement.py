LIMIT = 180
WARNING = 150


class Enforcer:
    def __init__(self, backend):
        self.backend = backend
        self.notify = None
        self.warned = []

    def send(self, text):
        if self.notify is not None:
            self.notify("FocusGuard", text)

    def check(self, window, kind, seconds):
        if kind != "unproductive":
            return False

        name = window.app_name
        if seconds >= WARNING and name not in self.warned:
            self.warned.append(name)
            self.send(name + " is unproductive. It will close in " + str(LIMIT - seconds) + " seconds.")

        if seconds < LIMIT:
            return False

        self.send("Time's up! Closing " + name + ".")
        self.backend.close_app(window.pid)
        if name in self.warned:
            self.warned.remove(name)
        return True
