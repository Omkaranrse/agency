# ADR 0006: GitHub Version Control and Cloudflare Pages Deployment Workflow

## Status
Accepted

## Context
Deploying websites requires a secure, auditable handoff to version control and content delivery networks. The system must create repositories, push versioned branches, produce preview deployments, conduct automated smoke tests, and promote to production upon approval.

## Decision
We implemented `GitHubAdapter` (implementing `GitPort`) and `CloudflarePagesAdapter` (implementing `DeployPort`):
1. **GitHub Adapter**: Generates repositories (`workspaces/{project_id}`), commits generated Astro code with atomic commit SHAs, and manages preview branches.
2. **Cloudflare Pages Adapter**: Directs deployment tarballs to Cloudflare Pages API, producing isolated preview URLs (`{revision}.pages.dev`) and promoting approved commits to custom domains.
3. **Automated Smoke Tests**: Preview deployments undergo post-deployment HTTP smoke testing with SSRF-safe hostname allowlisting (`*.pages.dev`, `*.agency.run`).
4. **Staging Isolation**: Evaluations and tests never publish to public GitHub repos or create production Cloudflare deployments; they utilize `FakeGit` and `FakeDeploy`.

## Consequences
- Every website has full Git provenance and commit history.
- Preview environments allow live testing before production promotion.
- Production deployments are protected from failed smoke tests or unapproved commits.
