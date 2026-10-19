"""In-memory fake implementation of GitPort for testing."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from agency.application.errors import GitError
from agency.application.ports.git import GitCommitInfo, GitPort, GitRepoInfo


class FakeGit(GitPort):
    """Deterministic in-memory Git adapter managing virtual commits and branches."""

    def __init__(self) -> None:
        self._repos: dict[str, dict[str, Any]] = {}
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated VCS failure."""
        self._simulated_error = error

    def clear(self) -> None:
        """Reset repository state and calls."""
        self._repos.clear()
        self._simulated_error = None
        self.calls.clear()

    def init_repository(
        self, project_id: str, default_branch: str = "main"
    ) -> GitRepoInfo:
        """Initialize virtual repository with root commit."""
        if self._simulated_error:
            raise self._simulated_error

        initial_sha = hashlib.sha1(f"{project_id}-init".encode()).hexdigest()
        initial_commit = GitCommitInfo(
            commit_sha=initial_sha,
            branch=default_branch,
            message="Initial project commit",
            author="Agency System",
            committed_at=datetime.now(UTC),
        )

        self._repos[project_id] = {
            "default_branch": default_branch,
            "branches": [default_branch],
            "commits": {initial_sha: initial_commit},
            "head": initial_sha,
        }

        self.calls.append({"op": "init_repository", "project_id": project_id})
        return GitRepoInfo(
            project_id=project_id,
            default_branch=default_branch,
            current_commit=initial_sha,
            branches=[default_branch],
        )

    def create_branch(
        self, project_id: str, branch_name: str, base_branch: str | None = None
    ) -> None:
        """Create a new branch pointer."""
        if self._simulated_error:
            raise self._simulated_error
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        if branch_name in repo["branches"]:
            raise GitError(f"Branch '{branch_name}' already exists.")

        repo["branches"].append(branch_name)
        self.calls.append(
            {
                "op": "create_branch",
                "project_id": project_id,
                "branch": branch_name,
            }
        )

    def commit_changes(
        self,
        project_id: str,
        message: str,
        branch: str = "main",
        author: str = "Agency AI",
    ) -> GitCommitInfo:
        """Record a commit on the target branch."""
        if self._simulated_error:
            raise self._simulated_error
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        if branch not in repo["branches"]:
            raise GitError(f"Branch '{branch}' does not exist in repo '{project_id}'.")

        now = datetime.now(UTC)
        sha = hashlib.sha1(
            f"{project_id}-{branch}-{message}-{now.isoformat()}".encode()
        ).hexdigest()

        commit = GitCommitInfo(
            commit_sha=sha,
            branch=branch,
            message=message,
            author=author,
            committed_at=now,
        )

        repo["commits"][sha] = commit
        repo["head"] = sha
        self.calls.append(
            {
                "op": "commit_changes",
                "project_id": project_id,
                "commit_sha": sha,
            }
        )
        return commit

    def get_commit_info(self, project_id: str, commit_sha: str) -> GitCommitInfo:
        """Retrieve stored commit metadata."""
        if self._simulated_error:
            raise self._simulated_error
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        commit = repo["commits"].get(commit_sha)
        if not isinstance(commit, GitCommitInfo):
            raise GitError(f"Commit '{commit_sha}' not found.")
        return commit

    def get_repo_info(self, project_id: str) -> GitRepoInfo:
        """Retrieve repository metadata."""
        if self._simulated_error:
            raise self._simulated_error
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        return GitRepoInfo(
            project_id=project_id,
            default_branch=repo["default_branch"],
            current_commit=repo["head"],
            branches=list(repo["branches"]),
        )
