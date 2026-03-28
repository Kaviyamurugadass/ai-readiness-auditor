"""AI-Readiness Auditor environment — core logic."""
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from openenv.core.env_server import Environment
from ai_readiness_auditor.models import AuditorAction, AuditorObservation, AuditorState
from .grading import grade_project


TASK_DESCRIPTIONS = {
    "easy": (
        "You are auditing a Python project for AI-readiness. Your task is to:\n"
        "1. Create a README.md with sections: Installation, Usage/Quickstart, API Reference, and code examples\n"
        "2. Create an llms.txt file with a structured description of the project and relevant links\n\n"
        "The project is a data pipeline library called 'dataflow'. "
        "Review the source files to understand what it does, then create these documentation files."
    ),
    "medium": (
        "You are auditing a Python project for AI-readiness. Your task is to:\n"
        "1. Create CLAUDE.md with project overview, build/run commands, and directory structure\n"
        "2. Create AGENTS.md with instructions for AI agents working on this codebase\n"
        "3. Create .env.example listing required environment variables\n"
        "4. Create an examples/ folder with working Python example files\n"
        "5. Fix __init__.py to include __all__ listing public exports\n"
        "6. Add a py.typed marker file\n"
        "7. Create CONTRIBUTING.md with contribution guidelines, code style, and development setup\n"
        "8. Create .pre-commit-config.yaml with linting and formatting hooks\n\n"
        "The project is a data pipeline library called 'dataflow'."
    ),
    "hard": (
        "You are auditing a Python project for AI-readiness. Complete ALL of the following:\n"
        "1. Everything from the easy task (README.md, llms.txt)\n"
        "2. Everything from the medium task (CLAUDE.md, AGENTS.md, .env.example, examples/, "
        "__init__.py __all__, py.typed, CONTRIBUTING.md, .pre-commit-config.yaml)\n"
        "3. Fix Python source code: add type hints to all functions, add docstrings, "
        "fix function/variable names to follow PEP 8 (snake_case, descriptive names), "
        "make error messages descriptive\n\n"
        "The project is a data pipeline library called 'dataflow'."
    ),
}


class AuditorEnvironment(Environment[AuditorAction, AuditorObservation, AuditorState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._state = AuditorState()
        self._project_files = {}

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditorObservation:
        task_id = kwargs.get("task_id", "easy")
        if task_id not in TASK_DESCRIPTIONS:
            task_id = "easy"

        # Load sample project from disk
        self._project_files = self._load_sample_project()

        # Grade initial state
        grade = grade_project(self._project_files, task_id)

        # Initialize state
        self._state = AuditorState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_id=task_id,
            max_steps=7,
            current_score=grade.score,
            project_files=dict(self._project_files),
        )

        return AuditorObservation(
            done=False,
            reward=0.0,
            task_id=task_id,
            task_description=TASK_DESCRIPTIONS[task_id],
            project_files=dict(self._project_files),
            score=grade.score,
            score_breakdown=grade.breakdown,
            feedback=grade.feedback,
            steps_remaining=self._state.max_steps,
        )

    def step(
        self,
        action: AuditorAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> AuditorObservation:
        self._state.step_count += 1

        # Apply file changes from the agent
        for path, content in action.files.items():
            self._project_files[path] = content

        # Sync state
        self._state.project_files = dict(self._project_files)

        # Re-grade
        grade = grade_project(self._project_files, self._state.task_id)

        # Delta-based reward
        reward = round(grade.score - self._state.current_score, 4)
        self._state.current_score = grade.score

        # Check if done
        steps_remaining = self._state.max_steps - self._state.step_count
        done = steps_remaining <= 0 or grade.score >= 1.0 or action.done

        return AuditorObservation(
            done=done,
            reward=reward,
            task_id=self._state.task_id,
            task_description=TASK_DESCRIPTIONS[self._state.task_id],
            project_files=dict(self._project_files),
            score=grade.score,
            score_breakdown=grade.breakdown,
            feedback=grade.feedback,
            steps_remaining=max(steps_remaining, 0),
        )

    @property
    def state(self) -> AuditorState:
        return self._state

    def _load_sample_project(self) -> dict[str, str]:
        """Load sample project files from disk into a dict."""
        project_dir = Path(__file__).parent / "sample_project"
        files = {}
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(project_dir))
                # Normalize to forward slashes
                rel_path = rel_path.replace(os.sep, "/")
                files[rel_path] = file_path.read_text(encoding="utf-8")
        return files
