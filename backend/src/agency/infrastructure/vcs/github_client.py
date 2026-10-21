"""HTTP client communicating with the GitHub REST API."""

import base64
import logging
import random
import time
from typing import Any

import httpx

from agency.application.errors import (
    GitAmbiguityError,
    GitAuthenticationError,
    GitConflictError,
    GitError,
    GitRateLimitError,
)
from agency.infrastructure.vcs.config import GitHubSettings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Resilient HTTP client for GitHub REST API interactions."""

    def __init__(
        self,
        settings: GitHubSettings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Agency-VCS/1.0",
        }
        if settings.token:
            self._headers["Authorization"] = f"Bearer {settings.token}"

        self._client = httpx.Client(
            base_url=settings.api_base_url,
            headers=self._headers,
            timeout=settings.request_timeout,
            transport=transport,
            verify=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _sanitize_headers_for_logging(
        self, headers: dict[str, Any] | httpx.Headers
    ) -> dict[str, str]:
        sanitized = dict(headers)
        if "Authorization" in sanitized:
            sanitized["Authorization"] = "Bearer ***"
        if "authorization" in sanitized:
            sanitized["authorization"] = "Bearer ***"
        return sanitized

    def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        expected_status: tuple[int, ...] = (200,),
    ) -> httpx.Response:
        """Execute request with bounded retries, jittered backoff, and error mapping."""
        if not self.settings.token:
            raise GitAuthenticationError(
                "GitHub token is unconfigured. Set GITHUB_TOKEN environment variable."
            )

        attempt = 0
        max_retries = max(1, self.settings.max_retries)

        while True:
            attempt += 1
            try:
                res = self._client.request(
                    method=method,
                    url=path,
                    json=json_data,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= max_retries:
                    raise GitAmbiguityError(
                        f"GitHub operation '{method} {path}' timed out: {exc}"
                    ) from exc
                backoff = (2 ** (attempt - 1)) * 0.5 + random.uniform(0.1, 0.3)
                time.sleep(backoff)
                continue

            # 1. Rate limiting
            if res.status_code == 429 or (
                res.status_code == 403 and "rate limit" in res.text.lower()
            ):
                retry_after_str = res.headers.get("Retry-After")
                retry_after = (
                    float(retry_after_str)
                    if retry_after_str and retry_after_str.isdigit()
                    else 60.0
                )
                raise GitRateLimitError(
                    f"GitHub rate limit exceeded during '{method} {path}'.",
                    retry_after=retry_after,
                )

            # 2. Authentication and Authorization
            if res.status_code in (401, 403):
                raise GitAuthenticationError(
                    f"GitHub authentication/permission failure ({res.status_code}) "
                    f"on '{method} {path}': {res.text}"
                )

            # 3. Server errors with retry
            if res.status_code >= 500:
                if attempt >= max_retries:
                    raise GitAmbiguityError(
                        f"GitHub server error {res.status_code} on "
                        f"'{method} {path}': {res.text}"
                    )
                backoff = (2 ** (attempt - 1)) * 0.5 + random.uniform(0.1, 0.3)
                time.sleep(backoff)
                continue

            # 4. Expected or client responses
            return res

    def get_repo(self, owner: str, repo: str) -> dict[str, Any] | None:
        """Retrieve repository metadata if it exists."""
        res = self._request("GET", f"/repos/{owner}/{repo}", expected_status=(200, 404))
        if res.status_code == 404:
            return None
        if res.status_code != 200:
            raise GitError(f"Failed to get repository '{owner}/{repo}': {res.text}")
        return res.json()  # type: ignore[no-any-return]

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True,
    ) -> dict[str, Any]:
        """Create a new GitHub repository under organization or user account."""
        endpoint = (
            f"/orgs/{self.settings.owner}/repos"
            if self.settings.is_org and self.settings.owner
            else "/user/repos"
        )
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": False,
        }

        res = self._request(
            "POST",
            endpoint,
            json_data=payload,
            expected_status=(201, 422),
        )

        # Handle 422: repository may already exist
        if res.status_code == 422:
            owner = self.settings.owner
            if not owner:
                user_info = self.get_authenticated_user()
                owner = user_info["login"]
            existing = self.get_repo(owner, name)
            if existing:
                return existing
            raise GitConflictError(
                f"Repository '{name}' creation rejected with 422: {res.text}"
            )

        if res.status_code not in (200, 201):
            raise GitError(f"Failed to create repository '{name}': {res.text}")

        return res.json()  # type: ignore[no-any-return]

    def get_authenticated_user(self) -> dict[str, Any]:
        """Retrieve details of the authenticated GitHub user."""
        res = self._request("GET", "/user")
        if res.status_code != 200:
            raise GitAuthenticationError(f"Failed to get user profile: {res.text}")
        return res.json()  # type: ignore[no-any-return]

    def get_branch(self, owner: str, repo: str, branch: str) -> dict[str, Any] | None:
        """Retrieve branch reference information."""
        res = self._request("GET", f"/repos/{owner}/{repo}/branches/{branch}")
        if res.status_code == 404:
            return None
        if res.status_code != 200:
            raise GitError(
                f"Failed to get branch '{branch}' in '{owner}/{repo}': {res.text}"
            )
        return res.json()  # type: ignore[no-any-return]

    def get_commit(self, owner: str, repo: str, commit_sha: str) -> dict[str, Any]:
        """Retrieve commit metadata."""
        res = self._request("GET", f"/repos/{owner}/{repo}/commits/{commit_sha}")
        if res.status_code == 404:
            raise GitError(f"Commit '{commit_sha}' not found in '{owner}/{repo}'.")
        if res.status_code != 200:
            raise GitError(f"Failed to get commit '{commit_sha}': {res.text}")
        return res.json()  # type: ignore[no-any-return]

    def create_tree(
        self,
        owner: str,
        repo: str,
        base_tree_sha: str | None,
        files: dict[str, str | bytes],
    ) -> str:
        """Create a new Git tree object containing the given files."""
        tree_items = []
        for path, content in files.items():
            if isinstance(content, bytes):
                encoded = base64.b64encode(content).decode("ascii")
                # Create blob for binary file
                blob_res = self._request(
                    "POST",
                    f"/repos/{owner}/{repo}/git/blobs",
                    json_data={"content": encoded, "encoding": "base64"},
                )
                if blob_res.status_code != 201:
                    raise GitError(
                        f"Failed to create blob for '{path}': {blob_res.text}"
                    )
                sha = blob_res.json()["sha"]
                tree_items.append(
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": sha,
                    }
                )
            else:
                tree_items.append(
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "content": content,
                    }
                )

        payload: dict[str, Any] = {"tree": tree_items}
        if base_tree_sha:
            payload["base_tree"] = base_tree_sha

        res = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json_data=payload,
        )
        if res.status_code != 201:
            raise GitError(f"Failed to create tree in '{owner}/{repo}': {res.text}")
        return str(res.json()["sha"])

    def create_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree_sha: str,
        parents: list[str],
        author_name: str = "Agency AI",
    ) -> str:
        """Create a new Git commit object pointing to a tree."""
        payload = {
            "message": message,
            "tree": tree_sha,
            "parents": parents,
            "author": {
                "name": author_name,
                "email": "agency@agency.local",
            },
        }
        res = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json_data=payload,
        )
        if res.status_code != 201:
            raise GitError(f"Failed to create commit in '{owner}/{repo}': {res.text}")
        return str(res.json()["sha"])

    def update_ref(
        self,
        owner: str,
        repo: str,
        ref: str,
        commit_sha: str,
        force: bool = False,
    ) -> None:
        """Update branch reference to point to commit."""
        clean_ref = ref.lstrip("refs/").lstrip("heads/")
        res = self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/heads/{clean_ref}",
            json_data={"sha": commit_sha, "force": force},
        )
        if res.status_code != 200:
            raise GitError(f"Failed to update ref 'heads/{clean_ref}': {res.text}")

    def create_ref(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        commit_sha: str,
    ) -> None:
        """Create a new branch reference."""
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": commit_sha,
        }
        res = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json_data=payload,
        )
        if res.status_code == 422:
            raise GitConflictError(f"Branch '{branch_name}' already exists.")
        if res.status_code != 201:
            raise GitError(f"Failed to create branch '{branch_name}': {res.text}")
