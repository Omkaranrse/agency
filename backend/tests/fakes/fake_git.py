"""In-memory fake implementation of GitPort for testing."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from agency.application.errors import (
    GitAmbiguityError,
    GitAuthenticationError,
    GitConflictError,
    GitError,
    GitRateLimitError,
    GitValidationError,
)
from agency.application.ports.git import GitCommitInfo, GitPort, GitRepoInfo

SENSITIVE_PATTERNS = (".env", ".pem", ".key", "id_rsa", "credentials")


class FakeGit(GitPort):
    """Deterministic in-memory Git adapter managing virtual commits and branches."""

    def __init__(self, owner: str = "agency-org") -> None:
        self.owner = owner
        self._repos: dict[str, dict[str, Any]] = {}
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []
        self.simulate_conflict: bool = False
        self.simulate_rate_limit: float | None = None
        self.simulate_timeout: bool = False
        self.simulate_auth_failure: bool = False

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated VCS failure."""
        self._simulated_error = error

    def clear(self) -> None:
        """Reset repository state and calls."""
        self._repos.clear()
        self._simulated_error = None
        self.calls.clear()
        self.simulate_conflict = False
        self.simulate_rate_limit = None
        self.simulate_timeout = False
        self.simulate_auth_failure = False

    def _check_simulation_hooks(self, op: str) -> None:
        if self._simulated_error:
            raise self._simulated_error
        if self.simulate_auth_failure:
            raise GitAuthenticationError(f"Simulated 401 Bad credentials on {op}")
        if self.simulate_rate_limit is not None:
            raise GitRateLimitError(
                f"Simulated 429 Rate limit exceeded on {op}",
                retry_after=self.simulate_rate_limit,
            )
        if self.simulate_timeout:
            raise GitAmbiguityError(f"Simulated connection timeout during {op}")

    def init_repository(
        self, project_id: str, default_branch: str = "main"
    ) -> GitRepoInfo:
        """Initialize virtual repository with root commit idempotently."""
        self._check_simulation_hooks("init_repository")

        repo_name = f"agency-{project_id}"
        repo_url = f"https://github.com/{self.owner}/{repo_name}"

        # If repo exists, handle conflict simulation or idempotent return
        if project_id in self._repos:
            if self.simulate_conflict:
                raise GitConflictError(
                    f"Repository '{repo_name}' already exists on remote."
                )
            existing = self._repos[project_id]
            self.calls.append(
                {"op": "init_repository", "project_id": project_id, "reused": True}
            )
            return GitRepoInfo(
                project_id=project_id,
                default_branch=existing["default_branch"],
                current_commit=existing["head"],
                branches=list(existing["branches"]),
                repo_name=repo_name,
                repo_url=repo_url,
                owner=self.owner,
            )

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
            "files": {},
        }

        self.calls.append(
            {"op": "init_repository", "project_id": project_id, "reused": False}
        )
        return GitRepoInfo(
            project_id=project_id,
            default_branch=default_branch,
            current_commit=initial_sha,
            branches=[default_branch],
            repo_name=repo_name,
            repo_url=repo_url,
            owner=self.owner,
        )

    def create_branch(
        self, project_id: str, branch_name: str, base_branch: str | None = None
    ) -> None:
        """Create a new branch pointer."""
        self._check_simulation_hooks("create_branch")
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        if branch_name in repo["branches"]:
            raise GitConflictError(f"Branch '{branch_name}' already exists.")

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
        files: dict[str, str | bytes] | None = None,
    ) -> GitCommitInfo:
        """Record a commit on the target branch with optional files."""
        self._check_simulation_hooks("commit_changes")
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        if branch not in repo["branches"]:
            raise GitError(f"Branch '{branch}' does not exist in repo '{project_id}'.")

        # Validate secret exclusion and safe paths
        if files:
            for path in files:
                if ".." in path or path.startswith("/"):
                    raise GitValidationError(f"Unsafe file path detected: '{path}'")
                for sensitive in SENSITIVE_PATTERNS:
                    if sensitive in path:
                        raise GitValidationError(
                            f"Sensitive file disallowed from VCS publish: '{path}'"
                        )
            repo["files"].update(files)

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
                "file_count": len(files) if files else 0,
            }
        )
        return commit

    def get_commit_info(self, project_id: str, commit_sha: str) -> GitCommitInfo:
        """Retrieve stored commit metadata."""
        self._check_simulation_hooks("get_commit_info")
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        commit = repo["commits"].get(commit_sha)
        if not isinstance(commit, GitCommitInfo):
            raise GitError(f"Commit '{commit_sha}' not found.")
        return commit

    def get_repo_info(self, project_id: str) -> GitRepoInfo:
        """Retrieve repository metadata."""
        self._check_simulation_hooks("get_repo_info")
        if project_id not in self._repos:
            raise GitError(f"Repository for project '{project_id}' not found.")

        repo = self._repos[project_id]
        repo_name = f"agency-{project_id}"
        return GitRepoInfo(
            project_id=project_id,
            default_branch=repo["default_branch"],
            current_commit=repo["head"],
            branches=list(repo["branches"]),
            repo_name=repo_name,
            repo_url=f"https://github.com/{self.owner}/{repo_name}",
            owner=self.owner,
        )
