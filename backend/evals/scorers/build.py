"""Build success scorer verifying command status and expected output artifacts."""

from pathlib import Path

from evals.schemas import BuildScore


def score_build(
    exit_code: int,
    artifact_dir: Path | None,
    required_routes: list[str] | None = None,
) -> BuildScore:
    """Evaluate static site compilation success with artifact existence verification.

    A build is successful only if:
    1. Exit code is 0.
    2. Artifact directory exists and contains index.html.
    3. Required page routes exist if specified.
    """
    routes = required_routes or ["index.html"]
    if exit_code != 0:
        return BuildScore(
            success=False,
            exit_code=exit_code,
            artifacts_present=False,
            required_routes_present=False,
            details=f"Build command failed with exit code {exit_code}.",
        )

    if artifact_dir is None or not artifact_dir.exists():
        return BuildScore(
            success=False,
            exit_code=exit_code,
            artifacts_present=False,
            required_routes_present=False,
            details="Build returned exit code 0 but artifact directory does not exist.",
        )

    # Check for primary index file
    index_candidates = [
        artifact_dir / "index.html",
        artifact_dir / "dist" / "index.html",
        artifact_dir / "site" / "index.html",
    ]
    artifacts_present = any(p.exists() and p.is_file() for p in index_candidates)

    if not artifacts_present:
        return BuildScore(
            success=False,
            exit_code=exit_code,
            artifacts_present=False,
            required_routes_present=False,
            details=(
                "Build returned exit code 0 but missing required index.html output."
            ),
        )

    # Check required routes
    missing_routes: list[str] = []
    base = artifact_dir / "dist" if (artifact_dir / "dist").exists() else artifact_dir
    for route in routes:
        clean = route.strip("/").removesuffix(".html")
        if not clean or clean == "index":
            continue
        # Route can be /about.html or /about/index.html
        direct_file = base / f"{clean}.html"
        dir_file = base / clean / "index.html"
        if not (direct_file.exists() or dir_file.exists()):
            missing_routes.append(clean)

    routes_present = len(missing_routes) == 0
    details = (
        "Build succeeded with all expected artifacts."
        if routes_present
        else f"Build succeeded but missing generated routes: {missing_routes}"
    )

    return BuildScore(
        success=routes_present,
        exit_code=exit_code,
        artifacts_present=artifacts_present,
        required_routes_present=routes_present,
        details=details,
    )
