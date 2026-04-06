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

An OpenEnv environment where AI agents audit and improve projects for AI-readiness.

## TL;DR

An AI agent receives a broken Python project and must fix it step-by-step.

- **Input:** Broken project (no docs, bad code, no AI instruction files)
- **Action:** Agent edits/creates files each step
- **Reward:** Delta-based (improvement in quality score)
- **Goal:** Reach a 1.0 AI-readiness score

Think of it as: **"codebase improvement as a game environment for AI agents."**

Inspired by [Factory.ai's Agent Readiness](https://factory.ai/news/agent-readiness) framework.

## Why This Matters

AI coding agents often fail not because of model limitations, but because the codebase is not structured for AI consumption. Missing documentation, unclear structure, and poor code quality make it difficult for agents to reason and act effectively.

This environment tests whether an agent can **improve the codebase itself** — a critical capability for real-world autonomous development systems.

## Example Episode (Easy Task)

```
Reset  → Agent sees: 5 broken Python files, no README, no docs
         Score: 0.00

Step 1 → Agent creates README.md with Installation, Usage, API sections
         Score: 0.00 → 0.50  |  Reward: +0.50

Step 2 → Agent creates llms.txt with project description and links
         Score: 0.50 → 0.78  |  Reward: +0.28

Step 3 → Agent improves README — adds Python code examples, more content
         Score: 0.78 → 0.94  |  Reward: +0.16

Step 4 → Agent resubmits same files, no real improvement
         Score: 0.94 → 0.94  |  Reward: 0.00  (no reward for no-ops)

Done   → Final score: 0.94 in 4 steps
         Total reward collected: +0.94 (sum of all step rewards = final score)
```

## Tasks & Grading Rubric

### Task 1: README & llms.txt (Easy)

**Goal:** Create project documentation that AI agents and developers can read.

**What's tested:** File presence + content quality. This task evaluates documentation generation capabilities.

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

**What's tested:** Understanding project structure, creating multiple files with correct content, and fixing code configuration.

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

**What's tested:** Code understanding, refactoring ~38 functions across 5 files, plus everything from easy and medium tasks.

**Composite scoring:**
- Easy checks (Task 1): **25% weight**
- Medium checks (Task 2): **25% weight**
- Code quality checks: **50% weight**

#### Code Quality Checks (applied to 5 source files, ~38 functions)

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
| **Hard** | Code reasoning + refactoring | Understand code intent, rename functions, add type hints |

## Why This Environment is Challenging

- **Multi-step reasoning across files** — agent must read 5 source files to understand the project before writing docs
- **Combines documentation + code refactoring** — the hard task requires both writing and coding skills
- **Large action space** — agent can create/modify any file with any content
- **Penalizes destructive edits** — submitting invalid Python yields negative reward
- **Genuinely hard for frontier models** — baseline scores 0.40 on hard task; renaming 38 functions correctly while preserving functionality is non-trivial

The sample project has:
- **~38 functions** with 0% type hints, 0% docstrings
- **12 functions** with camelCase names (violating PEP 8)
- **All error messages** are generic ("bad", "error")
- **Zero** documentation files

## Action Space

The agent submits file changes each step:

```json
{
    "files": {
        "README.md": "# DataFlow\n\n## Installation\n...",
        "src/dataflow/loader.py": "def load_file(path: str) -> list:\n    ..."
    },
    "done": false
}
```

- Agent can create new files and update existing files in one step
- Keys are relative paths, values are full file content
- Invalid Python in `.py` files scores 0.0 for code quality (penalty for destructive changes)

## Observation Space

After each step, the agent receives:

| Field | Type | Description |
|-------|------|-------------|
| `episode_id` | string | Unique identifier for this episode |
| `task_id` | string | "easy", "medium", or "hard" |
| `task_description` | string | Detailed instructions for the task |
| `project_files` | dict | Current state of ALL project files (path -> content) |
| `score` | float | Current aggregate score (0.0-1.0) |
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
| Agent adds README (score 0.0 -> 0.5) | +0.5 | Positive: good improvement |
| Agent adds llms.txt (score 0.5 -> 0.9) | +0.4 | Positive: more improvement |
| Agent submits same content again | 0.0 | Zero: no reward for no-ops |
| Agent breaks valid Python | Negative | Penalty: code quality dropped |

**Properties:**
- Sum of rewards across episode = final score (telescoping sum)
- Partial credit at every step (not just binary end-of-episode)
- Penalizes destructive actions (submitting invalid code)
- Episode ends when: score >= 1.0, steps run out (max 7), or agent sets `done: true`

## Baseline Agent

The baseline agent uses an OpenAI-compatible LLM to play all 3 tasks:

1. Reads project files + feedback from the observation
2. Generates improved/new files using the LLM
3. Submits files to the environment
4. Iterates until max steps or score >= 0.95

This provides a reproducible reference score for comparison.

| Task | Score | Steps | Interpretation |
|------|-------|-------|----------------|
| Easy | 1.00 | 1 | Documentation generation is straightforward for LLMs |
| Medium | 0.87 | 7 | Requires multiple AI instruction files and project structure fixes |
| Hard | 0.40 | 7 | Code refactoring genuinely challenges smaller models |

*Baseline model: meta-llama/Llama-3.1-8B-Instruct via HuggingFace Inference API (free)*

## OpenEnv Compliance

This environment follows the OpenEnv specification:

- `reset()` returns initial observation with project files and task description
- `step(action)` returns observation + delta reward + done flag
- Typed Pydantic models for Action, Observation, and State
- Deterministic grading (ast + regex, no LLM in the loop)
- Reproducible baseline with consistent scores
- Passes `openenv validate`

## Setup

### Local Development

```bash
pip install -e .
uvicorn server.app:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t ai-readiness-auditor .
docker run -p 8000:8000 ai-readiness-auditor
```

### Run Baseline

```bash
export HF_TOKEN="your-hf-token"
python inference.py
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
├── models.py             # Pydantic: AuditorAction, AuditorObservation, AuditorState
├── client.py             # WebSocket client (AuditorEnv)
├── inference.py          # Inference script (uses HF Inference API)
├── server/
│   ├── app.py            # FastAPI + custom endpoints
│   ├── environment.py    # Core logic: reset/step/state
│   └── grading.py        # Deterministic scoring (ast + regex)
├── data/
│   └── sample_project/   # The "broken" project agents must fix
│       └── src/dataflow/ # 5 files, ~38 functions, deliberately bad
├── static/
│   └── index.html        # Interactive dashboard UI
├── Dockerfile
├── openenv.yaml
└── README.md
```

## License

MIT
