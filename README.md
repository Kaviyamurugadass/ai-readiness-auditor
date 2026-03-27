# AI-Readiness Auditor

An OpenEnv environment where AI agents audit and improve projects for AI-readiness — adding documentation, AI instruction files, and fixing code quality.

## What It Does

The environment gives an AI agent a deliberately AI-unfriendly Python project (no README, no docs, bad naming, no type hints) and challenges it to make the project AI-ready. The agent submits file changes each step and receives a deterministic score (0.0–1.0) based on how much it improved.

## Tasks

| Task | Difficulty | Agent's Goal | Grading |
|------|-----------|-------------|---------|
| **README & llms.txt** | Easy | Create README.md with proper sections + llms.txt | Section checks, content validation |
| **AI Files & Structure** | Medium | Create CLAUDE.md, AGENTS.md, .env.example, examples/, fix __init__.py, add py.typed | File existence, content quality |
| **Full AI-Readiness Audit** | Hard | Everything above + fix Python code (type hints, docstrings, PEP 8 naming, error messages) | Composite: docs + structure + code quality via ast |

## Action Space

The agent submits a dictionary of file changes:

```python
{
    "files": {
        "README.md": "# Project Name\n\n## Installation\n...",
        "src/dataflow/loader.py": "def load_file(path: str) -> list:\n    ..."
    },
    "done": false  # Set to true to finish early
}
```

## Observation Space

The agent receives:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | "easy", "medium", or "hard" |
| `task_description` | string | What the agent should do |
| `project_files` | dict | Current state of all project files |
| `score` | float | Current score (0.0–1.0) |
| `score_breakdown` | dict | Per-check scores |
| `feedback` | list | What's still missing |
| `steps_remaining` | int | Steps left (max 7) |
| `reward` | float | Score improvement since last step |

## Setup

### Local Development

```bash
# Install dependencies
pip install -e .

# Start server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/tasks
```

### Docker

```bash
docker build -t ai-readiness-auditor .
docker run -p 8000:8000 ai-readiness-auditor
```

### Run Baseline

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"  # or any OpenAI-compatible API
export OPENAI_MODEL="openrouter/free"
python -m ai_readiness_auditor.baseline
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tasks` | GET | List available tasks + action schema |
| `/grader` | POST | Grade project files for a given task |
| `/baseline` | POST | Run baseline inference |
| `/schema` | GET | Action/Observation/State schemas |
| `/docs` | GET | Interactive API documentation |

## Baseline Scores

| Task | Score | Steps |
|------|-------|-------|
| Easy | TBD | TBD |
| Medium | TBD | TBD |
| Hard | TBD | TBD |

*(Scores will be updated after baseline run completes)*

## Architecture

```
ai_readiness_auditor/
├── models.py          # Pydantic: AuditorAction, AuditorObservation, AuditorState
├── client.py          # WebSocket client (AuditorEnv)
├── baseline.py        # OpenAI-compatible baseline agent
└── server/
    ├── app.py         # FastAPI + custom endpoints
    ├── environment.py # Core logic: reset/step/state
    ├── grading.py     # Deterministic scoring (ast + regex)
    └── sample_project/# The "broken" project agents must fix
```

## Reward Design

- **Delta-based:** reward = new_score - old_score each step
- Positive for improvements, zero for no-ops, negative for regressions
- Sum of rewards across episode equals final score

## License

MIT
