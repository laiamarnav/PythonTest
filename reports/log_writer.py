class LogWriter:
    def __init__(self, path: str):
        self.path = path

    def write(self, lines):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("SUMMARY REPORT\n")
            f.write("-" * 60 + "\n")
            if lines:
                f.write("\n".join(lines) + "\n")
            else:
                f.write("No blocked packages or issues found.\n")
