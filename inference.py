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
                        log_step(step=step, action="llm_call", reward=0.00, done=False, error=error)
                        break
                    llm_output = response.choices[0].message.content or ""
                except Exception as e:
                    error = str(e)
                    log_step(step=step, action="llm_call", reward=0.00, done=False, error=error)
                    break

                files = parse_file_response(llm_output)
                if not files:
                    error = "no_files_parsed"
                    log_step(step=step, action="parse", reward=0.00, done=False, error=error)
                    break

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

def run_inference(env_url: str = "http://localhost:8000") -> dict:
    """Run inference on all 3 tasks."""
    if not API_KEY:
        print("[END] success=false steps=0 score=0.00 rewards=", flush=True)
        return {"error": "API key not set. Set HF_TOKEN or OPENAI_API_KEY."}

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
