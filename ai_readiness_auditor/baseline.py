"""Baseline inference script for the AI-Readiness Auditor.

Uses an OpenAI-compatible API (GLM/ZhipuAI) to run a simple agent
that attempts all 3 tasks. Reads OPENAI_API_KEY from environment.

Usage:
    # Set your API key
    export OPENAI_API_KEY="your-key-here"

    # Run against local server
    python -m ai_readiness_auditor.baseline

    # Run against deployed HF Space
    python -m ai_readiness_auditor.baseline --url https://your-space.hf.space
"""
import os
import re
import json
import argparse

from openai import OpenAI
from ai_readiness_auditor.client import AuditorEnv
from ai_readiness_auditor.models import AuditorAction


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
MODEL = os.environ.get("OPENAI_MODEL", "glm-4.5-air")

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

def parse_file_response(response_text: str) -> dict[str, str]:
    """Parse LLM response into a dict of {path: content}.

    Expected format:
    ===FILE: path/to/file===
    content
    ===END FILE===
    """
    files = {}
    pattern = r'===FILE:\s*(.+?)===\s*\n(.*?)===END FILE==='
    matches = re.findall(pattern, response_text, re.DOTALL)

    for path, content in matches:
        path = path.strip()
        content = content.strip() + "\n"
        files[path] = content

    # Fallback: if no file blocks found, try to use entire response as README
    if not files and len(response_text.strip()) > 50:
        files["README.md"] = response_text.strip() + "\n"

    return files


def build_prompt(observation) -> str:
    """Build a user prompt from the current observation."""
    prompt_parts = [
        f"## Task\n{observation.task_description}\n",
        f"## Current Score: {observation.score:.2f} / 1.00",
        f"## Steps Remaining: {observation.steps_remaining}\n",
    ]

    # Add feedback
    if observation.feedback:
        prompt_parts.append("## Feedback (what's still missing)")
        for fb in observation.feedback:
            prompt_parts.append(f"- {fb}")
        prompt_parts.append("")

    # Add current project files
    prompt_parts.append("## Current Project Files\n")
    for path in sorted(observation.project_files.keys()):
        content = observation.project_files[path]
        prompt_parts.append(f"### {path}")
        prompt_parts.append(f"```\n{content}\n```\n")

    return "\n".join(prompt_parts)


# ---------------------------------------------------------------------------
# Run baseline for one task
# ---------------------------------------------------------------------------

def run_task(env_url: str, task_id: str, llm_client: OpenAI) -> dict:
    """Run the baseline agent on a single task. Returns results dict."""
    print(f"\n{'='*60}")
    print(f"Task: {task_id}")
    print(f"{'='*60}")

    with AuditorEnv(base_url=env_url).sync() as env:
        result = env.reset(task_id=task_id)
        obs = result.observation

        print(f"  Reset -> Score: {obs.score:.4f}")

        step = 0
        while not result.done and obs.steps_remaining > 0:
            step += 1

            # Build prompt
            user_prompt = build_prompt(obs)

            # Call LLM
            try:
                response = llm_client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=4096,
                )
                if not response.choices:
                    print(f"  Step {step}: Empty response from LLM: {response}")
                    break
                llm_output = response.choices[0].message.content or ""
            except Exception as e:
                print(f"  Step {step}: LLM error: {type(e).__name__}: {e}")
                break

            # Parse response into files
            files = parse_file_response(llm_output)

            if not files:
                print(f"  Step {step}: No files parsed from response, stopping")
                break

            # Submit to environment
            result = env.step(AuditorAction(files=files))
            obs = result.observation

            print(f"  Step {step}: Submitted {len(files)} files -> Score: {obs.score:.4f} (reward: {result.reward:+.4f})")

            # Stop if score is very high (diminishing returns)
            if obs.score >= 0.95:
                print(f"  Score >= 0.95, stopping early")
                break

    # Save output files
    output_dir = os.path.join("outputs", task_id)
    os.makedirs(output_dir, exist_ok=True)
    for path, content in obs.project_files.items():
        file_path = os.path.join(output_dir, path)
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"  Output saved to: {output_dir}/")

    final = {
        "task_id": task_id,
        "final_score": obs.score,
        "steps_taken": step,
        "breakdown": obs.score_breakdown,
    }
    print(f"  Final: {obs.score:.4f} in {step} steps")
    return final


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_baseline(env_url: str = "http://localhost:8000") -> dict:
    """Run baseline on all 3 tasks. Returns results dict."""
    if not API_KEY:
        print("ERROR: OPENAI_API_KEY not set. Set it with:")
        print("  export OPENAI_API_KEY='your-key-here'")
        return {"error": "OPENAI_API_KEY not set"}

    llm_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    print(f"Baseline: model={MODEL}, base_url={BASE_URL}")
    print(f"Environment: {env_url}")

    results = {}
    for task_id in ["easy", "medium", "hard"]:
        try:
            results[task_id] = run_task(env_url, task_id, llm_client)
        except Exception as e:
            print(f"  ERROR on {task_id}: {e}")
            results[task_id] = {"task_id": task_id, "error": str(e)}

    # Summary
    print(f"\n{'='*60}")
    print("BASELINE RESULTS")
    print(f"{'='*60}")
    for task_id, r in results.items():
        score = r.get("final_score", "ERROR")
        steps = r.get("steps_taken", "?")
        print(f"  {task_id:8s}: {score} ({steps} steps)")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run AI-Readiness Auditor baseline")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Environment server URL")
    args = parser.parse_args()

    results = run_baseline(args.url)
    print(f"\n{json.dumps(results, indent=2, default=str)}")


if __name__ == "__main__":
    main()
