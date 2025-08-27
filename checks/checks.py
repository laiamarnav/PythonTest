# checks/checks.py
from .base_check import BaseCheck

class Check(BaseCheck):
    def __init__(self, check_type, runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr):
        self.check_type = check_type
        super().__init__(runner, blocked_packages, whitelist_projects, whitelist_nugets, reporter, tag_pr)
