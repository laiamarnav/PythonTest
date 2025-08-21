class Logger:
    """Simple console logger with color support."""

    ANSI = {
        "BOLD_RED": "\033[1;31m",
        "BOLD_YELLOW": "\033[1;33m",
        "RESET": "\033[0m",
    }

    def info(self, msg: str) -> None:
        print(msg)

    def warning(self, msg: str) -> None:
        print(f"{self.ANSI['BOLD_YELLOW']}{msg}{self.ANSI['RESET']}")

    def error(self, msg: str) -> None:
        print(f"{self.ANSI['BOLD_RED']}{msg}{self.ANSI['RESET']}")
