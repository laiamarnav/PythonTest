ANSI = {
    "BOLD_RED": "\033[1;31m",
    "BOLD_YELLOW": "\033[1;33m",
    "RESET": "\033[0m"
}

LOG_FILE = "nugets.log"
summary_lines = []

def log(msg: str):
    print(msg)

def log_summary(msg: str):
    summary_lines.append(msg)
    if msg.startswith("ERROR"):
        print(f"{ANSI['BOLD_RED']}{msg}{ANSI['RESET']}")
    elif msg.startswith("WARNING"):
        print(f"{ANSI['BOLD_YELLOW']}{msg}{ANSI['RESET']}")
    else:
        print(msg)

def get_summary_lines():
    return summary_lines

def clear_summary():
    summary_lines.clear()

def write_summary_to_file():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("SUMMARY REPORT\n")
        f.write("-" * 60 + "\n")
        if summary_lines:
            f.write("\n".join(summary_lines) + "\n")
        else:
            f.write("No blocked packages or issues found.\n")
