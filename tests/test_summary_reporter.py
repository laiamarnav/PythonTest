from reports.summary_reporter import SummaryReporter


class DummyLogger:
    def __init__(self):
        self.info_msgs = []
        self.warning_msgs = []
        self.error_msgs = []

    def info(self, msg):
        self.info_msgs.append(msg)

    def warning(self, msg):
        self.warning_msgs.append(msg)

    def error(self, msg):
        self.error_msgs.append(msg)


def test_add_accumulates_and_logs():
    logger = DummyLogger()
    reporter = SummaryReporter(logger)
    reporter.add("ERROR:")
    reporter.add("WARNING:")
    reporter.add("all good")

    assert reporter.lines == ["ERROR:", "WARNING:", "all good"]
    assert logger.error_msgs == ["ERROR:"]
    assert logger.warning_msgs == ["WARNING:"]
    assert logger.info_msgs == ["all good"]


def test_write_to_file_with_lines(tmp_path):
    reporter = SummaryReporter()
    reporter.add("ERROR: ")
    reporter.add("all good")
    file_path = tmp_path / "nugets.log"
    reporter.write_to_file(str(file_path))
    content = file_path.read_text()
    assert content == (
        "SUMMARY REPORT\n"
        + "-" * 60
        + "\nERROR: \nall good\n"
    )


def test_write_to_file_without_lines(tmp_path):
    reporter = SummaryReporter()
    file_path = tmp_path / "nugets.log"
    reporter.write_to_file(str(file_path))
    content = file_path.read_text()
    assert content == (
        "SUMMARY REPORT\n" + "-" * 60 + "\nNo blocked packages or issues found.\n"
    )
