"""Unit tests verifying port contracts and in-memory fake implementations."""

import pytest
from pydantic import BaseModel, HttpUrl
from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_git import FakeGit
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.errors import (
    DeployError,
    GitError,
    LLMError,
    RepositoryError,
    SandboxError,
    SandboxNotFoundError,
    SandboxSecurityError,
)
from agency.application.ports.deploy import DeployPort
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.git import GitPort
from agency.application.ports.llm import LLMPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.ports.sandbox import ExecResult, SandboxPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.events import RunStarted


# 1. Interface conformance tests
def test_fakes_implement_port_contracts() -> None:
    """Verify that every fake implements its respective abstract port interface."""
    assert isinstance(FakeRunRepository(), RunRepositoryPort)
    assert isinstance(FakeEventBus(), EventBusPort)
    assert isinstance(FakeLLM(), LLMPort)
    assert isinstance(FakeSandbox(), SandboxPort)
    assert isinstance(FakeGit(), GitPort)
    assert isinstance(FakeDeploy(), DeployPort)


# 2. FakeRunRepository tests
def test_fake_run_repository_lifecycle_and_isolation() -> None:
    """Verify FakeRunRepository save, read, list, count, and copy isolation."""
    repo = FakeRunRepository()
    run = Run(run_id="run-repo-test", project_id="proj-1")

    repo.save(run)
    assert repo.count() == 1
    assert repo.count(RunState.CREATED) == 1
    assert repo.count(RunState.COMPLETED) == 0

    # Ensure deep copy mutation isolation
    fetched = repo.get_by_id("run-repo-test")
    assert fetched is not None
    fetched.project_id = "mutated-outside"

    fresh = repo.get_by_id("run-repo-test")
    assert fresh is not None
    assert fresh.project_id == "proj-1"

    # Test error simulation
    repo.set_failure(RepositoryError("Simulated error"))
    with pytest.raises(RepositoryError):
        repo.get_by_id("run-repo-test")

    repo.set_failure(None)
    assert repo.get_by_id("run-repo-test") is not None

    # Test invalid limit/offset directly on repo
    with pytest.raises(RepositoryError, match="Limit must be between 1 and 100"):
        repo.list(limit=0)
    with pytest.raises(RepositoryError, match="Offset must be >= 0"):
        repo.list(offset=-1)

    repo.clear()
    assert repo.count() == 0


# 3. FakeEventBus tests
def test_fake_event_bus_lifecycle_and_ordering() -> None:
    """Verify FakeEventBus preserves ordering and supports inspection."""
    bus = FakeEventBus()
    e1 = RunStarted(run_id="r1", project_id="p1")
    e2 = RunStarted(run_id="r2", project_id="p2")

    bus.publish(e1)
    bus.publish_all([e2])

    assert len(bus.events) == 2
    assert bus.events[0].run_id == "r1"
    assert bus.events[1].run_id == "r2"

    bus.set_failure(RuntimeError("Bus failure"))
    with pytest.raises(RuntimeError):
        bus.publish(e1)
    with pytest.raises(RuntimeError):
        bus.publish_all([e1])

    bus.clear()
    assert len(bus.events) == 0


# 4. FakeLLM tests
class MockSchema(BaseModel):
    summary: str
    confidence: float


def test_fake_llm_structured_generation() -> None:
    """Verify FakeLLM structured output validation and call tracking."""
    llm = FakeLLM()
    mock_resp = MockSchema(summary="A web app spec", confidence=0.98)
    llm.set_response(MockSchema, mock_resp)

    result = llm.generate_structured(
        schema=MockSchema,
        prompt="Analyze user brief",
        role="system_architect",
    )

    assert result.summary == "A web app spec"
    assert result.confidence == 0.98
    assert len(llm.calls) == 1
    assert llm.calls[0]["role"] == "system_architect"

    # Deep copy isolation check
    result.summary = "Mutated summary"
    fresh = llm.generate_structured(MockSchema, "prompt", "role")
    assert fresh.summary == "A web app spec"

    # Validation checks
    with pytest.raises(LLMError, match="Prompt cannot be empty"):
        llm.generate_structured(MockSchema, "   ", "role")

    with pytest.raises(LLMError, match="Role cannot be empty"):
        llm.generate_structured(MockSchema, "prompt", "   ")

    # Missing schema configuration
    class UnregisteredSchema(BaseModel):
        title: str

    with pytest.raises(LLMError, match="No mock response configured"):
        llm.generate_structured(UnregisteredSchema, "prompt", "role")

    # Simulated failure
    llm.set_failure(LLMError("API rate limit exceeded"))
    with pytest.raises(LLMError, match="API rate limit exceeded"):
        llm.generate_structured(MockSchema, "prompt", "role")

    llm.clear()
    assert len(llm.calls) == 0


# 5. FakeSandbox tests
def test_fake_sandbox_lifecycle_and_security() -> None:
    """Verify FakeSandbox filesystem, execution, and path traversal security."""
    sbx = FakeSandbox()

    # Create sandbox
    sbx_id = sbx.create(template="node-nextjs", timeout_seconds=60)
    assert sbx_id.startswith("sbx-")

    # Write & read file
    sbx.write_file(sbx_id, "src/index.ts", "console.log('hello');")
    content = sbx.read_file(sbx_id, "src/index.ts")
    assert content == "console.log('hello');"

    # Copy out
    data = sbx.copy_out(sbx_id, "src/index.ts")
    assert data == b"console.log('hello');"

    # Exec standard command
    res = sbx.exec(sbx_id, ["npm", "run", "build"])
    assert res.exit_code == 0
    assert res.stdout == "OK"

    # Exec configured custom response
    sbx.set_exec_response(
        "npm test", ExecResult(exit_code=1, stdout="", stderr="Tests failed")
    )
    fail_res = sbx.exec(sbx_id, "npm test")
    assert fail_res.exit_code == 1
    assert fail_res.stderr == "Tests failed"

    # Path traversal security: path starting with / or ..
    with pytest.raises(SandboxSecurityError):
        sbx.write_file(sbx_id, "/etc/passwd", "root")
    with pytest.raises(SandboxSecurityError):
        sbx.read_file(sbx_id, "../sensitive.txt")

    # Missing file
    with pytest.raises(SandboxError, match="File not found"):
        sbx.read_file(sbx_id, "missing.txt")

    # Destroy
    sbx.destroy(sbx_id)
    with pytest.raises(SandboxNotFoundError):
        sbx.read_file(sbx_id, "src/index.ts")


# 6. FakeGit tests
def test_fake_git_repository_and_commit_management() -> None:
    """Verify FakeGit initialization, branching, and commit history."""
    git = FakeGit()

    # Init
    repo_info = git.init_repository(project_id="proj-web-app", default_branch="main")
    assert repo_info.project_id == "proj-web-app"
    assert repo_info.default_branch == "main"
    assert len(repo_info.current_commit) == 40  # SHA-1 hash length

    # Branch
    git.create_branch("proj-web-app", "feature/prototype")
    info = git.get_repo_info("proj-web-app")
    assert "feature/prototype" in info.branches

    # Duplicate branch rejected
    with pytest.raises(GitError, match="already exists"):
        git.create_branch("proj-web-app", "feature/prototype")

    # Commit
    commit = git.commit_changes(
        project_id="proj-web-app",
        message="feat: initial prototype",
        branch="feature/prototype",
    )
    assert commit.branch == "feature/prototype"
    assert commit.message == "feat: initial prototype"

    # Retrieve commit info
    retrieved_commit = git.get_commit_info("proj-web-app", commit.commit_sha)
    assert retrieved_commit.commit_sha == commit.commit_sha

    # Error simulation
    git.set_failure(GitError("VCS remote timeout"))
    with pytest.raises(GitError, match="VCS remote timeout"):
        git.get_repo_info("proj-web-app")


# 7. FakeDeploy tests
def test_fake_deploy_staging_and_production() -> None:
    """Verify FakeDeploy staging and production URL generation."""
    deployer = FakeDeploy()

    # Staging deployment
    staging = deployer.deploy_staging(project_id="shop-app", commit_sha="abc1234")
    assert str(staging.preview_url) == "https://shop-app-preview.agency.run/"
    assert staging.production_url is None
    assert staging.provider == "fake-cloud"

    # Production deployment
    prod = deployer.deploy_production(project_id="shop-app", commit_sha="abc1234")
    assert str(prod.preview_url) == "https://shop-app-preview.agency.run/"
    assert str(prod.production_url) == "https://shop-app.agency.run/"

    # Get latest deployment
    latest = deployer.get_deployment("shop-app")
    assert latest is not None
    assert latest.production_url == HttpUrl("https://shop-app.agency.run")

    # Error simulation
    deployer.set_failure(DeployError("Deployment provider unavailable"))
    with pytest.raises(DeployError, match="Deployment provider unavailable"):
        deployer.deploy_staging("shop-app", "abc")
