# System Demo Walkthrough — Agency

This guide provides a reproducible, step-by-step walkthrough to demonstrate the full multi-agent delivery workflow using deterministic fixtures and fake providers.

**Safety Guarantee**:
- Uses `FakeLLM`, `FakeGit`, and `FakeDeploy` adapters.
- Requires zero API keys or external credentials.
- Incurs zero cost.
- Does not publish public GitHub repositories or deploy live websites.

---

## 1. Prerequisites
- Python 3.12+ with virtual environment activated (`source .venv/bin/activate`).
- Node.js 20+ and pnpm (`pnpm --version`).
- Terminal window with `curl` and `jq` installed.

---

## 2. Step-by-Step Demo Script

### Step 1: Start the Local Services
```bash
# Terminal 1: Launch FastAPI API server in development mode
PYTHONPATH=backend/src:backend uvicorn agency.interfaces.api.app:create_app --factory --port 8000

# Terminal 2: Launch Next.js Operator Dashboard
cd dashboard && pnpm dev
```
- Open browser to `http://localhost:3000`.
- Verify API liveness:
  ```bash
  curl -s http://localhost:8000/health | jq .
  ```

---

### Step 2: Create a Representative Brief
Submit a client brief for an architecture portfolio:
```bash
curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "brief": {
      "client_name": "Maya Lin",
      "site_type": "Architecture & Sculpture Portfolio",
      "pages": ["home", "work", "about", "contact"],
      "tone": "minimal, contemplative, architectural",
      "content_notes": "Memorial architect and sculptor focused on landscape and environmental memory.",
      "links": ["https://example.com/mayalin"]
    },
    "project_id": "maya-lin-demo"
  }' | jq .
```
Expected output:
```json
{
  "run_id": "run-maya-lin-demo-...",
  "project_id": "maya-lin-demo",
  "status": "CREATED",
  "current_stage": "created"
}
```

---

### Step 3: Stream Live Progress (SSE)
Connect to the Server-Sent Events stream to observe multi-agent progress:
```bash
RUN_ID="<paste-run-id-from-step-2>"
curl -N http://localhost:8000/api/v1/runs/$RUN_ID/events
```
You will observe:
1. `RUN_CREATED` — Brief accepted and initial state initialized.
2. `SPEC_GENERATED` — PM agent generates structured `ProductSpec`.
3. `TOKENS_GENERATED` — Designer agent generates `DesignTokens`.
4. `PROTOTYPE_READY` — Prototype packaged; workflow enters `AWAITING_APPROVAL`.

---

### Step 4: Review Prototype and Approve Deployment
In the dashboard at `http://localhost:3000/runs/$RUN_ID`:
1. Inspect the generated page structure and design tokens.
2. Review the static preview.
3. Submit human approval to proceed to production build:
```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/approve \
  -H "Content-Type: application/json" \
  -d '{"revision": 0, "approver": "lead-operator"}' | jq .
```

---

### Step 5: Observe Build, QA, and Simulated Deployment
The pipeline resumes from the approval checkpoint:
1. `BUILD_COMPLETED` — Astro site components built.
2. `QA_PASSED` — Automated QA checks pass (Astro build exit 0, required routes generated, SEO tags verified).
3. `DEPLOYMENT_COMPLETED` — Cloudflare Pages deployment completed (simulated URL: `https://maya-lin-demo.pages.dev`).
4. `RUN_COMPLETED` — Handover report generated and temporary sandbox destroyed.

Inspect final status:
```bash
curl -s http://localhost:8000/api/v1/runs/$RUN_ID | jq .
```

---

## 3. Recording a Demo GIF (Terminal / Browser)
To capture this flow as an animated GIF for documentation or presentations:
1. Use `vhs` (Charm) or `asciinema` + `agg`:
   ```bash
   # Install VHS if available
   brew install vhs
   # Run automated VHS script
   vhs docs/demo.tape
   ```
2. Or use macOS native screen recorder (`Cmd + Shift + 5`), select the dashboard window, and convert using `ffmpeg`:
   ```bash
   ffmpeg -i demo_recording.mov -vf "fps=10,scale=1080:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" demo.gif
   ```
