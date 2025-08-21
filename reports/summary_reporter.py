from typing import List

from core.logger import Logger


class SummaryReporter:
    def __init__(self, logger: Logger | None = None):
        self.logger = logger or Logger()
        self.lines: List[str] = []

    def add(self, msg: str) -> None:
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
