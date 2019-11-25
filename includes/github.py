# import standard modules
import os
from github import Github


class Repository():
    def __init__(self):
        self.github = Github(os.environ.get("GIT_TOKEN"))
        self.repo = self.github.get_repo(os.environ.get("GIT_REPO"))

    def get_issues(self):
        issues = self.repo.get_issues()

        return issues

    def create_issue(self, title, body, label_name):
        label = self.repo.get_label(label_name)

        return self.repo.create_issue(title=title, body=body, labels=[label])
