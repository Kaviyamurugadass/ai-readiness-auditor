"""Inference script for the AI-Readiness Auditor.

Uses OpenAI-compatible API to run an agent against all 3 tasks.

Required env vars:
    API_BASE_URL  — LLM API endpoint (e.g. https://openrouter.ai/api/v1)
    MODEL_NAME    — model to use (e.g. openrouter/free)
    HF_TOKEN      — Hugging Face token

Usage:
    python inference.py
    python inference.py --url https://your-space.hf.space
"""
import os
import re
import json
import argparse
import sys

from openai import OpenAI
from client import AuditorEnv
from models import AuditorAction


# ---------------------------------------------------------------------------
# Config — uses the required env var names
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Also support OPENAI_API_KEY as fallback for local testing
API_KEY = HF_TOKEN or os.environ.get("OPENAI_API_KEY", "")

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

You can include multiple files in one response. Example:

===FILE: README.md===
# My Project
...content...
===END FILE===

===FILE: llms.txt===
# My Project
...content...
===END FILE===

IMPORTANT:
- Use the exact format above (===FILE: path=== and ===END FILE===)
- Include the FULL file content, not just changes
- Make sure Python code blocks in markdown are valid Python
- Follow PEP 8 naming conventions for Python code
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_file_response(response_text):
    """Parse LLM response into a dict of {path: content}."""
    files = {}
    pattern = r'===FILE:\s*(.+?)===\s*\n(.*?)===END FILE==='
    matches = re.findall(pattern, response_text, re.DOTALL)
    for path, content in matches:
        path = path.strip()
        content = content.strip() + "\n"
        files[path] = content
    if not files and len(response_text.strip()) > 50:
        files["README.md"] = response_text.strip() + "\n"
    return files


def build_prompt(observation):
    """Build a user prompt from the current observation."""
    prompt_parts = [
        f"## Task\n{observation.task_description}\n",
        f"## Current Score: {observation.score:.2f} / 1.00",
        f"## Steps Remaining: {observation.steps_remaining}\n",
    ]
    if observation.feedback:
        prompt_parts.append("## Feedback (what's still missing)")
        for fb in observation.feedback:
            prompt_parts.append(f"- {fb}")
        prompt_parts.append("")
    prompt_parts.append("## Current Project Files\n")
    for path in sorted(observation.project_files.keys()):
        content = observation.project_files[path]
        prompt_parts.append(f"### {path}")
        prompt_parts.append(f"```\n{content}\n```\n")
    return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# Run inference for one task
# ---------------------------------------------------------------------------

def run_task(env_url, task_id, llm_client):
    """Run the agent on a single task with structured logging."""
    print(f"[START] task={task_id}")

    with AuditorEnv(base_url=env_url).sync() as env:
        result = env.reset(task_id=task_id)
        obs = result.observation

        print(f"[STEP] task={task_id} step=0 action=reset score={obs.score:.4f} reward=0.0 done=false")

        step = 0
        while not result.done and obs.steps_remaining > 0:
            step += 1
            user_prompt = build_prompt(obs)

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
                    print(f"[STEP] task={task_id} step={step} action=llm_call error=empty_response")
                    break
                llm_output = response.choices[0].message.content or ""
            except Exception as e:
                print(f"[STEP] task={task_id} step={step} action=llm_call error={type(e).__name__}")
                break

            files = parse_file_response(llm_output)
            if not files:
                print(f"[STEP] task={task_id} step={step} action=parse error=no_files_parsed")
                break

            result = env.step(AuditorAction(files=files))
            obs = result.observation
            reward = result.reward or 0.0

            print(f"[STEP] task={task_id} step={step} action=submit files={len(files)} score={obs.score:.4f} reward={reward:+.4f} done={obs.done}")

            if obs.score >= 0.95:
                break

    print(f"[END] task={task_id} final_score={obs.score:.4f} steps={step}")

    return {
        "task_id": task_id,
        "final_score": obs.score,
        "steps_taken": step,
        "breakdown": obs.score_breakdown,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_inference(env_url="http://localhost:8000"):
    """Run inference on all 3 tasks."""
    if not API_KEY:
        print("[END] error=API_KEY_NOT_SET message='Set HF_TOKEN or OPENAI_API_KEY'")
        return {"error": "API key not set. Set HF_TOKEN or OPENAI_API_KEY."}

    llm_client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    print(f"[START] inference model={MODEL_NAME} base_url={API_BASE_URL}")

    results = {}
    for task_id in ["easy", "medium", "hard"]:
        try:
            results[task_id] = run_task(env_url, task_id, llm_client)
        except Exception as e:
            print(f"[END] task={task_id} error={type(e).__name__}: {e}")
            results[task_id] = {"task_id": task_id, "error": str(e)}

    # Summary
    print(f"\n[START] summary")
    for task_id, r in results.items():
        score = r.get("final_score", "ERROR")
        steps = r.get("steps_taken", "?")
        print(f"[STEP] task={task_id} final_score={score} steps={steps}")
    print(f"[END] summary")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI-Readiness Auditor inference")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Environment server URL")
    args = parser.parse_args()

    results = run_inference(args.url)
    print(json.dumps(results, indent=2, default=str))
