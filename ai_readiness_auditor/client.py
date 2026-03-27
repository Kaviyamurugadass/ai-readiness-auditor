"""WebSocket client for the AI-Readiness Auditor environment."""
from typing import Any, Dict

from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from .models import AuditorAction, AuditorObservation, AuditorState


class AuditorEnv(EnvClient[AuditorAction, AuditorObservation, AuditorState]):

    def _step_payload(self, action: AuditorAction) -> Dict[str, Any]:
        return {"files": action.files, "done": action.done}

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[AuditorObservation]:
        obs_data = payload.get("observation", payload)
        return StepResult(
            observation=AuditorObservation(
                done=payload.get("done", False),
                reward=payload.get("reward"),
                task_id=obs_data.get("task_id", ""),
                task_description=obs_data.get("task_description", ""),
                project_files=obs_data.get("project_files", {}),
                score=obs_data.get("score", 0.0),
                score_breakdown=obs_data.get("score_breakdown", {}),
                feedback=obs_data.get("feedback", []),
                steps_remaining=obs_data.get("steps_remaining", 0),
            ),
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> AuditorState:
        return AuditorState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id", ""),
            max_steps=payload.get("max_steps", 7),
            current_score=payload.get("current_score", 0.0),
            project_files=payload.get("project_files", {}),
        )
