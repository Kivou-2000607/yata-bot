# import standard modules
from github import Github


class Repository():
    def __init__(self, token=None, repo=None):
        print("repo", repo)
        print("token", token)
        self.github = Github(token)
        self.repo = self.github.get_repo(repo)

    def get_issues(self):
        issues = self.repo.get_issues()

        return issues

    def create_issue(self, title, body, label_name):
        label = self.repo.get_label(label_name)

        return self.repo.create_issue(title=title, body=body, labels=[label])
