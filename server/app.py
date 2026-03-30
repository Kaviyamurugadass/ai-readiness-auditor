"""FastAPI app for the AI-Readiness Auditor environment."""
import os
from pathlib import Path
from typing import Dict
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openenv.core.env_server import create_fastapi_app

from models import AuditorAction, AuditorObservation
from server.environment import AuditorEnvironment
from server.grading import grade_project

# Create the OpenEnv API
app = create_fastapi_app(
    env=AuditorEnvironment,
    action_cls=AuditorAction,
    observation_cls=AuditorObservation,
)

# Serve custom static HTML dashboard
STATIC_DIR = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def root():
    """Serve the dashboard."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ---------------------------------------------------------------------------
# Custom endpoints required by the hackathon
# ---------------------------------------------------------------------------

@app.get("/tasks")
def get_tasks():
    """Return list of available tasks and action schema."""
    return {
        "tasks": [
            {
                "id": "easy",
                "name": "README & llms.txt",
                "description": "Create README.md with standard sections (Installation, Usage, API Reference, code examples) and llms.txt with project description and links for the given codebase",
                "difficulty": "easy",
                "max_steps": 7,
            },
            {
                "id": "medium",
                "name": "AI Files & Project Structure",
                "description": (
                    "Improve project structure for the given repository: "
                    "create CLAUDE.md, AGENTS.md, .env.example, examples/, "
                    "CONTRIBUTING.md, .pre-commit-config.yaml, "
                    "fix __init__.py with __all__, add py.typed"
                ),
                "difficulty": "medium",
                "max_steps": 7,
            },
            {
                "id": "hard",
                "name": "Full AI-Readiness Audit",
                "description": (
                    "Perform full AI-readiness audit on the given codebase: "
                    "all of easy + medium + refactor all Python functions (~38): "
                    "add type hints, add docstrings, rename to PEP 8 snake_case, "
                    "make error messages descriptive"
                ),
                "difficulty": "hard",
                "max_steps": 7,
            },
        ],
        "action_schema": AuditorAction.model_json_schema(),
    }


class GraderRequest(BaseModel):
    task_id: str = "easy"
    project_files: Dict[str, str] = {}


@app.api_route("/grader", methods=["GET", "POST"])
def run_grader(request: GraderRequest = None):
    """Grade project files for a given task. GET returns empty project score, POST accepts files."""
    if request is None:
        request = GraderRequest()
    result = grade_project(request.project_files, request.task_id)
    return {
        "task_id": request.task_id,
        "score": result.score,
        "breakdown": result.breakdown,
        "feedback": result.feedback,
    }


@app.api_route("/baseline", methods=["GET", "POST"])
def run_baseline_endpoint():
    """Run baseline inference directly (no WebSocket, no self-connection)."""
    import os
    from openai import OpenAI
    from baseline import parse_file_response, build_prompt, SYSTEM_PROMPT

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.z.ai/api/paas/v4/")
    model = os.environ.get("OPENAI_MODEL", "glm-4.5-air")

    if not api_key:
        return {"error": "OPENAI_API_KEY not set"}

    llm_client = OpenAI(api_key=api_key, base_url=base_url)
    results = {}

    for task_id in ["easy", "medium", "hard"]:
        try:
            env = AuditorEnvironment()
            obs = env.reset(task_id=task_id)
            step = 0

            for _ in range(7):
                if obs.done:
                    break
                step += 1
                prompt = build_prompt(obs)
                try:
                    response = llm_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.0,
                        max_tokens=4096,
                    )
                    if not response.choices:
                        break
                    llm_output = response.choices[0].message.content or ""
                except Exception:
                    break

                files = parse_file_response(llm_output)
                if not files:
                    break

                from models import AuditorAction
                obs = env.step(AuditorAction(files=files))
                if obs.score >= 0.95:
                    break

            results[task_id] = {
                "task_id": task_id,
                "final_score": obs.score,
                "steps_taken": step,
                "breakdown": obs.score_breakdown,
            }
        except Exception as e:
            results[task_id] = {"task_id": task_id, "error": str(e)}

    return results


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
