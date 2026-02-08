import sys
import time
import threading
from contextlib import contextmanager

# --------- ANSI COLORS ----------
class Color:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"


# --------- TYPEWRITER ----------
def type_print(text, delay=0.01, color=Color.RESET, newline=True):
    for ch in text:
        sys.stdout.write(color + ch + Color.RESET)
        sys.stdout.flush()
        time.sleep(delay)
    if newline:
        sys.stdout.write("\n")
        sys.stdout.flush()


# --------- SPINNER ----------
_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

class Spinner:
    def __init__(self, text="", interval=0.1, color=Color.CYAN):
        self.text = text
        self.interval = interval
        self.color = color
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            sys.stdout.write(
                f"\r{self.color}{frame} {self.text}{Color.RESET}"
            )
            sys.stdout.flush()
            time.sleep(self.interval)
            i += 1

    def start(self):
        self._thread.start()

    def stop(self, final_text=None, success=True):
        self._stop.set()
        self._thread.join()
        symbol = "✓" if success else "✗"
        color = Color.GREEN if success else Color.RED
        msg = final_text or self.text
        sys.stdout.write(
            f"\r{color}{symbol} {msg}{Color.RESET}\n"
        )
        sys.stdout.flush()


# --------- CONTEXT MANAGER ----------
@contextmanager
def stage(text, *, color=Color.CYAN):
    spinner = Spinner(text=text, color=color)
    spinner.start()
    try:
        yield
        spinner.stop(text, success=True)
    except Exception:
        spinner.stop(text, success=False)
        raise
