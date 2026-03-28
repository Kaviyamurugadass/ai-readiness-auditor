---
title: AI-Readiness Auditor
emoji: 🔍
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
tags:
  - openenv
---

# AI-Readiness Auditor

An OpenEnv environment where AI agents audit and improve projects for AI-readiness — adding documentation, AI instruction files, and fixing code quality.

Inspired by [Factory.ai's Agent Readiness](https://factory.ai/news/agent-readiness) framework: when AI agents underperform, the issue is often the codebase environment, not the model.

## What It Does

The environment gives an AI agent a deliberately AI-unfriendly Python project (38 functions, 0% type hints, 0% docstrings, no README, no AI files) and challenges it to make the project AI-ready.

Each step:
1. Agent reads the project files + feedback
2. Agent submits improved/new files
3. Environment scores the changes deterministically (0.0–1.0)
4. Agent gets score + per-check breakdown + feedback on what's missing
5. Repeat (max 7 steps)

## Tasks & Grading Rubric

### Task 1: README & llms.txt (Easy)

**Goal:** Create project documentation that AI agents and developers can read.

**Difficulty:** File presence + content quality. Most LLMs can generate a good README.

| # | Check | Method | Pass Criteria |
|---|-------|--------|---------------|
| 1 | README.md exists | File exists | File is present and non-empty |
| 2 | Has Installation section | Heading regex (`## Installation`) | Heading found |
| 3 | Has Usage/Quickstart section | Heading regex (`## Usage`) | Heading found |
| 4 | Has API Reference section | Heading regex (`## API`) | Heading found |
| 5 | Has Python code blocks | Regex for ` ```python ` | At least 1 code block |
| 6 | Code blocks are valid Python | `ast.parse()` on each block | Fraction that parse successfully |
| 7 | Sufficient content (200+ words) | `len(content.split())` | `min(word_count / 200, 1.0)` |
| 8 | llms.txt exists | File exists | File is present and non-empty |
| 9 | llms.txt has structure | `#` heading check | Has at least one heading |
| 10 | llms.txt has links | URL regex (`https://`) | Has at least one link |

**Score = average of all 10 checks (each 0.0 or 1.0)**

---

### Task 2: AI Instruction Files & Project Structure (Medium)

**Goal:** Make the project navigable and usable by AI coding agents (Claude, Copilot, Cursor).

**Difficulty:** Requires understanding project structure, creating multiple files with correct content, and fixing code.

| # | Check | Method | Pass Criteria |
|---|-------|--------|---------------|
| 1 | CLAUDE.md exists | File exists | Non-empty |
| 2 | CLAUDE.md has overview section | Heading regex | "Overview"/"About"/"Project" heading found |
| 3 | CLAUDE.md has commands section | Heading regex | "Commands"/"Build"/"Run" heading found |
| 4 | CLAUDE.md has structure section | Heading regex | "Structure"/"Directory" heading found |
| 5 | AGENTS.md exists with content | File exists + word count | Exists and 50+ words |
| 6 | .env.example exists | File exists | Non-empty |
| 7 | .env.example has KEY=value | Regex `^[A-Z_]+=` | At least one variable |
| 8 | examples/ folder has .py files | Path check | At least one `examples/*.py` |
| 9 | Example files are valid Python | `ast.parse()` | Fraction that parse |
| 10 | `__init__.py` has `__all__` | AST check for `__all__` assignment | Assignment found |
| 11 | py.typed marker exists | File exists | Present (can be empty) |
| 12 | CONTRIBUTING.md exists | File exists | Non-empty |
| 13 | CONTRIBUTING.md has content | Word count | 50+ words |
| 14 | .pre-commit-config.yaml exists | File exists | Non-empty |

**Score = average of all 14 checks**

---

### Task 3: Full AI-Readiness Audit (Hard)

**Goal:** Complete AI-readiness overhaul — documentation, AI files, structure, AND code quality.

**Difficulty:** Requires code understanding, refactoring 38 functions across 5 files, plus everything from easy and medium tasks. Genuinely challenges frontier models.

**Composite scoring:**
- Easy checks (Task 1): **25% weight**
- Medium checks (Task 2): **25% weight**
- Code quality checks: **50% weight**

#### Code Quality Checks (applied to 5 source files, 38 functions)

| # | Check | Method | Score |
|---|-------|--------|-------|
| 1 | Type hint coverage | AST: count functions with all args + return annotated | `annotated / total` functions |
| 2 | Docstring coverage | AST: first body element is string constant | `docstringed / total` functions |
| 3 | PEP 8 naming | Regex: `^_?[a-z][a-z0-9_]*$` + length > 2 | `compliant / total` functions |
| 4 | Descriptive error messages | AST: `raise` statements have string args > 10 chars | `descriptive / total` raises |

**Code score = average of 4 checks**
**Final score = easy_score * 0.25 + medium_score * 0.25 + code_score * 0.50**

---

### Difficulty Curve

| Level | What's Tested | Skill Required |
|-------|--------------|----------------|
| **Easy** | File presence + content | Generate docs from reading code |
| **Medium** | Structure + correctness + multiple files | Understand project layout, create valid configs |
| **Hard** | Code reasoning + refactoring | Understand code intent, rename functions, add type hints across 38 functions |

The sample project has:
- **38 functions** with 0% type hints, 0% docstrings
- **12 functions** with camelCase names (violating PEP 8)
- **All error messages** are generic ("bad", "error")
- **Zero** documentation files

## Action Space

The agent submits a dictionary of file changes each step:

```python
{
    "files": {
        "README.md": "# DataFlow\n\n## Installation\n...",
        "src/dataflow/loader.py": "def load_file(path: str) -> list:\n    ..."
    },
    "done": false  // Set to true to finish early
}
```

- Agent can create new files and update existing files in one step
- Keys are relative paths, values are full file content
- Invalid Python in `.py` files scores 0.0 for code quality (penalty for destructive changes)

## Observation Space

After each step, the agent receives:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | "easy", "medium", or "hard" |
| `task_description` | string | Detailed instructions for the task |
| `project_files` | dict | Current state of ALL project files (path -> content) |
| `score` | float | Current aggregate score (0.0–1.0) |
| `score_breakdown` | dict | Per-check scores (e.g. `{"readme_exists": 1.0, "llms_txt_exists": 0.0}`) |
| `feedback` | list[str] | Human-readable feedback on what's still missing |
| `steps_remaining` | int | Steps left before episode ends (max 7) |
| `reward` | float | Score improvement since last step (delta) |
| `done` | bool | Whether the episode has ended |

## Reward Design

**Delta-based rewards** provide meaningful signal over the full trajectory:

```
reward = new_score - old_score
```

| Scenario | Reward | Signal |
|----------|--------|--------|
| Agent adds README (score 0.0 → 0.5) | +0.5 | Positive — good improvement |
| Agent adds llms.txt (score 0.5 → 0.9) | +0.4 | Positive — more improvement |
| Agent submits nothing useful | 0.0 | Zero — no change |
| Agent breaks valid Python | Negative | Penalty — code quality dropped |

**Properties:**
- Sum of rewards across episode = final score (telescoping sum)
- Partial credit at every step (not just binary end-of-episode)
- Penalizes destructive actions (submitting invalid code)
- Agent can finish early by setting `done: true`

## Baseline Scores

| Task | Score | Steps | Interpretation |
|------|-------|-------|----------------|
| Easy | 0.94 | 6 | Most LLMs can generate good docs |
| Medium | 1.00 | 7 | Achievable with multiple focused steps |
| Hard | 0.75 | 4 | Code refactoring is genuinely challenging |

*Baseline model: openrouter/free (auto-selected free model via OpenRouter)*

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
        └── src/dataflow/  # 5 files, 38 functions, deliberately bad
```

## License

MIT
