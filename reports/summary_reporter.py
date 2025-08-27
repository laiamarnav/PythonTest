from typing import Optional
from core.logger import Logger

class SummaryReporter:
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger()
        self.lines = []

    def add(self, msg: str):
        self.lines.append(msg)

        if msg.startswith("ERROR"):
            self.logger.error(msg)
        elif msg.startswith("WARNING"):
            self.logger.warning(msg)
        else:
            self.logger.info(msg)

    def has_errors(self) -> bool:
        return any(line.startswith("ERROR") for line in self.lines)

    def has_warnings(self) -> bool:
        return any(line.startswith("WARNING") for line in self.lines)

    def write_to_file(self, path: str = "nugets.log"):
        """Write the accumulated summary lines to a log file, monolith-style."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("SUMMARY REPORT\n")
            f.write("-" * 60 + "\n")
            if self.lines:
                f.write("\n".join(self.lines) + "\n")
            else:
                f.write("No blocked packages or issues found.\n")
