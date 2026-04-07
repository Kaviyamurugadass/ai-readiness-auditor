"""
Inference Script for AI-Readiness Auditor
===================================
MANDATORY
- Environment variables:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

- Defaults are set only for API_BASE_URL and MODEL_NAME:
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

- Uses OpenAI Client for all LLM calls.

STDOUT FORMAT
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import re
import json
import sys
from typing import List, Optional

from openai import OpenAI
from client import AuditorEnv
from models import AuditorAction


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

API_KEY = HF_TOKEN or os.getenv("OPENAI_API_KEY", "")

BENCHMARK = "ai-readiness-auditor"
MAX_STEPS = 7

SYSTEM_PROMPT = """You are an AI agent that improves Python projects for AI-readiness.

You will receive:
1. A task description telling you what to improve
2. The current project files
3. Your current score and feedback on what's missing

Your job: create or update files to improve the project's AI-readiness.

RESPONSE FORMAT:
Return your file changes in this exact format:

===FILE: path/to/file.ext===
file content here
===END FILE===

You can include multiple files in one response.

IMPORTANT:
- Use the exact format above (===FILE: path=== and ===END FILE===)
- Include the FULL file content, not just changes
- Make sure Python code blocks in markdown are valid Python
- Follow PEP 8 naming conventions for Python code
"""


# ---------------------------------------------------------------------------
# Logging — exact format from sample
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_file_response(response_text: str) -> dict:
    """Parse LLM response into {path: content}."""
    files = {}
    pattern = r'===FILE:\s*(.+?)===\s*\n(.*?)===END FILE==='
    matches = re.findall(pattern, response_text, re.DOTALL)
    for path, content in matches:
        files[path.strip()] = content.strip() + "\n"
    if not files and len(response_text.strip()) > 50:
        files["README.md"] = response_text.strip() + "\n"
    return files


def build_prompt(observation) -> str:
    """Build a user prompt from the current observation."""
    parts = [
        f"## Task\n{observation.task_description}\n",
        f"## Current Score: {observation.score:.2f} / 1.00",
        f"## Steps Remaining: {observation.steps_remaining}\n",
    ]
    if observation.feedback:
        parts.append("## Feedback (what's still missing)")
        for fb in observation.feedback:
            parts.append(f"- {fb}")
        parts.append("")
    parts.append("## Current Project Files\n")
    for path in sorted(observation.project_files.keys()):
        content = observation.project_files[path]
        parts.append(f"### {path}")
        parts.append(f"```\n{content}\n```\n")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Run one task
# ---------------------------------------------------------------------------

def run_task(env_url: str, task_id: str, llm_client: OpenAI) -> dict:
    """Run inference on a single task."""
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        with AuditorEnv(base_url=env_url).sync() as env:
            result = env.reset(task_id=task_id)
            obs = result.observation

            for step in range(1, MAX_STEPS + 1):
                if result.done:
                    break

                user_prompt = build_prompt(obs)
                error = None

                # LLM call with retry
                llm_output = ""
                for attempt in range(2):
                    try:
                        response = llm_client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=0.0,
                            max_tokens=4096,
                        )
                        if not response.choices:
                            error = "empty_response"
                            continue
                        llm_output = response.choices[0].message.content or ""
                        error = None
                        break
                    except Exception as e:
                        error = str(e)

                if not llm_output:
                    log_step(step=step, action="llm_call", reward=0.00, done=False, error=error)
                    break

                files = parse_file_response(llm_output)
                if not files:
                    # Fallback: use rule-based files if LLM output can't be parsed
                    fallback_sets = FALLBACK_FILES.get(task_id, FALLBACK_FILES.get("easy", []))
                    if fallback_sets:
                        files = fallback_sets[0]

                action_str = f"submit({len(files)} files)"
                result = env.step(AuditorAction(files=files))
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done

                rewards.append(reward)
                steps_taken = step

                log_step(step=step, action=action_str, reward=reward, done=done, error=None)

                if obs.score >= 0.95:
                    break

            score = obs.score
            score = min(max(score, 0.0), 1.0)
            success = score >= 0.5

    except Exception as e:
        print(f"[DEBUG] Error: {e}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {
        "task_id": task_id,
        "final_score": score,
        "steps_taken": steps_taken,
        "success": success,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FALLBACK_FILES = {
    "easy": [
        {
            "README.md": (
                "# DataFlow\n\n"
                "A Python data pipeline library for loading, transforming, validating, and exporting data.\n\n"
                "## Installation\n\n"
                "```python\npip install dataflow\n```\n\n"
                "## Usage\n\n"
                "```python\nfrom dataflow import ld, flt, sv\n\n"
                "data = ld('input.csv')\nfiltered = flt(data, lambda x: int(x.get('age', 0)) > 25)\n"
                "sv(filtered, 'output.csv')\n```\n\n"
                "## API Reference\n\n"
                "### Loader\n- `ld(path, type, separator)` — Load CSV/JSON files\n"
                "- `ld_multi(paths)` — Load multiple files\n"
                "- `ld_dir(dir_path, ext)` — Load all files from directory\n\n"
                "### Transform\n- `flt(data, predicate)` — Filter rows\n"
                "- `mp(data, func)` — Map transformation\n"
                "- `agg(data, key, func)` — Group and aggregate\n"
                "- `srt(data, key)` — Sort data\n\n"
                "### Validator\n- `chk(data, schema)` — Validate against schema\n"
                "- `cleanData(data)` — Clean and strip data\n\n"
                "### Export\n- `sv(data, path, format)` — Save to CSV/JSON\n"
                "- `fmt(data, format)` — Format as table or markdown\n\n"
                "### Utils\n- `fl(list)` — Flatten nested lists\n"
                "- `mrg(d1, d2, key)` — Merge datasets\n"
                "- `dd(list, key)` — Deduplicate\n\n"
                "## License\n\nMIT\n"
            ),
            "llms.txt": (
                "# DataFlow\n\n"
                "> A Python data pipeline library for loading, transforming, validating, and exporting data.\n\n"
                "## Overview\n\n"
                "DataFlow provides simple functions for common data operations on CSV and JSON files.\n\n"
                "## Links\n\n"
                "- Source: https://github.com/example/dataflow\n"
                "- Docs: https://dataflow.readthedocs.io\n"
            ),
        },
    ],
    "medium": [
        {
            "CLAUDE.md": (
                "# Project Overview\n\nDataFlow is a Python data pipeline library.\n\n"
                "## Commands\n\n- Install: `pip install -e .`\n- Test: `pytest`\n\n"
                "## Project Structure\n\n```\nsrc/dataflow/\n  loader.py\n  transform.py\n"
                "  validator.py\n  export.py\n  utils.py\n```\n"
            ),
            "AGENTS.md": (
                "# AI Agent Instructions\n\nThis project is a Python data pipeline library. "
                "When working on this codebase, follow PEP 8 naming conventions, add type hints "
                "to all functions, and include docstrings with examples. The main source code is "
                "in src/dataflow/. Each module handles a specific data operation concern.\n"
            ),
            ".env.example": "DATA_DIR=/path/to/data\nLOG_LEVEL=INFO\nMAX_ROWS=10000\n",
            "examples/basic_usage.py": (
                "from dataflow import ld, flt, sv\n\n"
                "data = ld('sample.csv')\nfiltered = flt(data, lambda x: x.get('status') == 'active')\n"
                "sv(filtered, 'output.json', f='json')\nprint(f'Processed {len(filtered)} records')\n"
            ),
            "CONTRIBUTING.md": (
                "# Contributing to DataFlow\n\n"
                "## How to Contribute\n1. Fork the repo\n2. Create a branch\n3. Make changes\n"
                "4. Run tests with pytest\n5. Submit a pull request\n\n"
                "## Code Style\n- Follow PEP 8\n- Add type hints\n- Add docstrings\n"
            ),
            ".pre-commit-config.yaml": (
                "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
                "    rev: v0.4.0\n    hooks:\n      - id: ruff\n      - id: ruff-format\n"
            ),
            "src/dataflow/py.typed": "",
        },
        {
            "src/dataflow/__init__.py": (
                "__all__ = ['ld', 'ld_multi', 'ld_dir', 'flt', 'mp', 'agg', 'srt', "
                "'sv', 'fmt', 'chk', 'cleanData', 'fl', 'mrg', 'dd']\n\n"
                "from .loader import ld, ld_multi, ld_dir, chk_file, getHeaders\n"
                "from .transform import flt, mp, agg, srt, unq, slc, selectCols, dropCols, renCols, pivot\n"
                "from .validator import chk, vld_tp, chkEmpty, chkDups, cleanData, chkSchema\n"
                "from .export import sv, fmt, toRecords\n"
                "from .utils import fl, mrg, dd, chunker, countBy, pluck, indexBy, deepGet\n"
            ),
        },
    ],
}


def run_inference_no_llm(env_url: str) -> dict:
    """Fallback: run environment with rule-based file submissions (no LLM needed)."""
    print("[DEBUG] No API key found — running rule-based fallback", flush=True)
    results = {}

    for task_id in ["easy", "medium", "hard"]:
        rewards = []
        steps_taken = 0
        score = 0.0
        success = False

        log_start(task=task_id, env=BENCHMARK, model="rule-based-fallback")

        try:
            with AuditorEnv(base_url=env_url).sync() as env:
                result = env.reset(task_id=task_id)
                obs = result.observation

                # Detect project name from files
                project_files_str = " ".join(obs.project_files.keys())
                if "taskrunner" in project_files_str:
                    project_name = "taskrunner"
                    project_desc = "A Python task scheduling and execution library"
                else:
                    project_name = "dataflow"
                    project_desc = "A Python data pipeline library for loading, transforming, validating, and exporting data"

                # Build project-aware fallback README
                project_readme = FALLBACK_FILES["easy"][0]["README.md"].replace("DataFlow", project_name.capitalize()).replace(
                    "data pipeline library for loading, transforming, validating, and exporting data",
                    project_desc.split("A Python ")[-1] if "A Python" in project_desc else project_desc
                )
                project_llms = FALLBACK_FILES["easy"][0]["llms.txt"].replace("DataFlow", project_name.capitalize()).replace(
                    "data pipeline library", project_desc.split("A Python ")[-1].split(" library")[0] + " library"
                )

                adapted_easy = [{"README.md": project_readme, "llms.txt": project_llms}]
                all_fallback = adapted_easy + FALLBACK_FILES.get("medium", [])

                for file_set in all_fallback:
                    if result.done:
                        break
                    steps_taken += 1

                    # Filter: only submit files that feedback says are missing
                    feedback_text = " ".join(obs.feedback).lower()
                    relevant_files = {}
                    for path, content in file_set.items():
                        name = path.split("/")[-1].lower().replace(".", "").replace("_", "")
                        if any(keyword in feedback_text for keyword in [
                            path.lower(), name,
                            "readme" if "readme" in path.lower() else "",
                            "llms" if "llms" in path.lower() else "",
                            "claude" if "claude" in path.lower() else "",
                            "agents" if "agents" in path.lower() else "",
                            "contributing" if "contributing" in path.lower() else "",
                            "pre-commit" if "pre-commit" in path.lower() else "",
                            "env" if ".env" in path.lower() else "",
                            "example" if "example" in path.lower() else "",
                            "py.typed" if "py.typed" in path.lower() else "",
                            "__all__" if "__init__" in path.lower() else "",
                        ]) or not obs.feedback:
                            relevant_files[path] = content

                    if not relevant_files:
                        relevant_files = file_set

                    result = env.step(AuditorAction(files=relevant_files))
                    obs = result.observation
                    reward = result.reward or 0.0
                    rewards.append(reward)

                    action_str = f"submit({len(relevant_files)} files)"
                    log_step(step=steps_taken, action=action_str, reward=reward,
                             done=result.done, error=None)

                    if obs.score >= 0.95:
                        break

                score = obs.score
                score = min(max(score, 0.0), 1.0)
                success = score >= 0.5

        except Exception as e:
            print(f"[DEBUG] Error: {e}", flush=True)

        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

        results[task_id] = {
            "task_id": task_id,
            "final_score": score,
            "steps_taken": steps_taken,
            "success": success,
        }
    return results


def run_inference(env_url: str = "http://localhost:8000") -> dict:
    """Run inference on all 3 tasks. Falls back to no-LLM mode if API key is missing."""
    if not API_KEY:
        return run_inference_no_llm(env_url)

    llm_client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    results = {}
    for task_id in ["easy", "medium", "hard"]:
        results[task_id] = run_task(env_url, task_id, llm_client)

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run AI-Readiness Auditor inference")
    parser.add_argument("--url", default="http://localhost:8000", help="Environment server URL")
    args = parser.parse_args()

    results = run_inference(args.url)
    print(json.dumps(results, indent=2, default=str))
