from typing import Dict, List, Optional
from pydantic import Field
from openenv.core.env_server import Action, Observation, State


class AuditorAction(Action):
    """Agent submits file changes — dict of relative path to file content."""
    files: Dict[str, str] = Field(
        description="Map of file paths to file contents. "
        "Keys are relative paths (e.g. 'README.md', 'src/dataflow/loader.py'). "
        "Values are the full file content as strings."
    )
    done: bool = Field(
        default=False,
        description="Set to True if the agent wants to finish early."
    )


class AuditorObservation(Observation):
    """What the agent sees after each step."""
    # Inherited: done (bool), reward (float|None), metadata (dict)
    task_id: str = Field(
        default="easy",
        description="Task identifier: 'easy', 'medium', or 'hard'"
    )
    task_description: str = Field(
        default="",
        description="Human-readable description of what the agent should do"
    )
    project_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Current state of all project files (path -> content)"
    )
    score: float = Field(
        default=0.0,
        description="Current grading score from 0.0 to 1.0"
    )
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-check scores (e.g. {'readme_exists': 1.0, 'llms_txt_exists': 0.0})"
    )
    feedback: List[str] = Field(
        default_factory=list,
        description="Human-readable feedback on what's still missing"
    )
    steps_remaining: int = Field(
        default=7,
        description="Number of steps the agent has left"
    )


class AuditorState(State):
    """Internal environment state tracked across steps."""
    # Inherited: episode_id (str|None), step_count (int)
    task_id: str = ""
    max_steps: int = 7
    current_score: float = 0.0
    project_files: Dict[str, str] = Field(default_factory=dict)
