"""GitPort definition for version control management."""

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GitCommitInfo(BaseModel):
    """Metadata representing a specific Git commit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    commit_sha: str = Field(min_length=7, max_length=40)
    branch: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=100)
    committed_at: datetime


class GitRepoInfo(BaseModel):
    """Metadata representing a managed project repository."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(min_length=1, max_length=100)
    default_branch: str = Field(default="main")
    current_commit: str = Field(min_length=7, max_length=40)
    branches: list[str] = Field(default_factory=list)
    repo_name: str | None = None
    repo_url: str | None = None
    owner: str | None = None


class GitPort(ABC):
    """Abstract port for managing Git repositories without remote side effects."""

    @abstractmethod
    def init_repository(
        self, project_id: str, default_branch: str = "main"
    ) -> GitRepoInfo:
        """Initialize a project repository and establish initial commit.

        Raises:
            GitError: If initialization fails.
        """

    @abstractmethod
    def create_branch(
        self, project_id: str, branch_name: str, base_branch: str | None = None
    ) -> None:
        """Create a new branch in the specified repository.

        Raises:
            GitError: If branch creation fails or branch already exists.
        """

    @abstractmethod
    def commit_changes(
        self,
        project_id: str,
        message: str,
        branch: str = "main",
        author: str = "Agency AI",
        files: dict[str, str | bytes] | None = None,
    ) -> GitCommitInfo:
        """Record a commit with the specified message on the target branch.

        Args:
            project_id: Unique project identifier.
            message: Commit message.
            branch: Target branch name.
            author: Commit author name.
            files: Optional mapping of relative file paths to content.

        Raises:
            GitError: If the repository or branch does not exist or commit fails.
        """

    def publish_source(
        self,
        project_id: str,
        files: dict[str, str | bytes],
        message: str,
        branch: str = "main",
        author: str = "Agency AI",
    ) -> GitCommitInfo:
        """Publish verified project source files into the repository."""
        return self.commit_changes(
            project_id=project_id,
            message=message,
            branch=branch,
            author=author,
            files=files,
        )

    @abstractmethod
    def get_commit_info(self, project_id: str, commit_sha: str) -> GitCommitInfo:
        """Retrieve details for a specific commit.

        Raises:
            GitError: If commit is not found.
        """

    @abstractmethod
    def get_repo_info(self, project_id: str) -> GitRepoInfo:
        """Retrieve current metadata for a project repository.

        Raises:
            GitError: If repository does not exist.
        """
