import time

LIMIT = 180
WARNING = 150


class Enforcer:
    def __init__(self, backend):
        self.backend = backend
        self.notify = None
        self.warned = []
        self.closing = {}

    def send(self, text):
        if self.notify is not None:
            self.notify("FocusGuard", text)

    def check(self, window, kind, seconds):
        if kind != "unproductive":
            self.closing.clear()
            return

        name = window.app_name
        if seconds >= WARNING and name not in self.warned:
            self.warned.append(name)
            self.send(name + " is unproductive. It will close in " + str(LIMIT - seconds) + " seconds.")

        if seconds < LIMIT:
            return

        if name not in self.closing:
            self.closing[name] = time.time()
            self.send("Time's up! Closing " + name + ".")
            self.backend.close_app(window.pid)
        elif time.time() - self.closing[name] >= 5:
            self.backend.close_app(window.pid, force=True)
            self.closing[name] = time.time()
