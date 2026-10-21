# Agency Agent Prompts

This directory contains versioned system prompts for the multi-agent delivery lifecycle in Agency.

## Directory Structure

```text
agents/prompts/
├── README.md
├── v1/
│   ├── pm_system.md
│   ├── designer_system.md
│   └── builder_system.md
└── v2/ (future versions)
```

## Versioning Policy

1. Prompts are immutable once released under a version directory (e.g., `v1`).
2. New behavior or model instructions must be introduced as a new version directory (e.g., `v2`).
3. Agents specify their target prompt version explicitly (defaulting to `v1`).
4. Fallback across prompt versions is strictly prohibited to guarantee deterministic agent behavior.
5. Never embed credentials, secrets, API keys, or private client data in prompt templates.
