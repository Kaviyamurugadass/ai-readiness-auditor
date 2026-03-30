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
STATIC_DIR = Path(__file__).parent / "static"
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


@app.post("/grader")
def run_grader(request: GraderRequest):
    """Grade a set of project files for a given task."""
    result = grade_project(request.project_files, request.task_id)
    return {
        "task_id": request.task_id,
        "score": result.score,
        "breakdown": result.breakdown,
        "feedback": result.feedback,
    }


@app.post("/baseline")
def run_baseline_endpoint():
    """Trigger baseline inference and return scores."""
    from baseline import run_baseline
    results = run_baseline("http://localhost:8000")
    return results


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
