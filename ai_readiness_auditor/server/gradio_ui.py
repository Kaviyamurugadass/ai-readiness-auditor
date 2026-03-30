"""Custom Gradio web interface for the AI-Readiness Auditor."""
import json
import gradio as gr


CUSTOM_CSS = """
.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.metric-card .label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.7;
}
.metric-card .value {
    font-size: 28px;
    font-weight: bold;
}
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}
.btn-row button {
    min-width: 160px;
}
"""


def build_ui(web_manager, action_fields, metadata, is_chat_env, title, quick_start_md):
    """Build a dashboard-style web interface."""

    with gr.Blocks(
        title="AI-Readiness Auditor",
        css=CUSTOM_CSS,
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.emerald,
            secondary_hue=gr.themes.colors.blue,
            neutral_hue=gr.themes.colors.slate,
        ),
    ) as demo:

        # State
        episode_active = gr.State(False)

        # ─── Header ───
        gr.Markdown(
            "# AI-Readiness Auditor\n"
            "*OpenEnv Interactive Environment*"
        )

        # ─── Metric Cards Row ───
        with gr.Row(equal_height=True):
            score_display = gr.Textbox(
                label="CURRENT SCORE", value="—", interactive=False,
                elem_classes=["metric-card"]
            )
            reward_display = gr.Textbox(
                label="LAST REWARD", value="—", interactive=False,
                elem_classes=["metric-card"]
            )
            steps_display = gr.Textbox(
                label="STEPS REMAINING", value="—", interactive=False,
                elem_classes=["metric-card"]
            )
            episode_status = gr.Textbox(
                label="EPISODE STATUS", value="Not started", interactive=False,
                elem_classes=["metric-card"]
            )

        # ─── Action Buttons Row ───
        with gr.Row(elem_classes=["btn-row"]):
            task_selector = gr.Dropdown(
                choices=["easy", "medium", "hard"],
                value="easy",
                label="Task",
                scale=1,
            )
            reset_btn = gr.Button("Reset Environment", variant="primary", scale=1)
            grade_btn = gr.Button("Grade Tasks", variant="secondary", scale=1)
            docs_btn = gr.Button("API Docs", variant="secondary", scale=1, link="/docs")

        # ─── Main Content ───
        with gr.Row():
            # Left — Feedback & Scores
            with gr.Column(scale=1):
                gr.Markdown("### Feedback")
                feedback_display = gr.Markdown(
                    "*Click **Reset Environment** to start a new episode*"
                )

                gr.Markdown("### Task Scores")
                breakdown_display = gr.DataFrame(
                    headers=["Check", "Score"],
                    datatype=["str", "number"],
                    value=[["—", 0.0]],
                    interactive=False,
                    wrap=True,
                )

            # Right — Take Action
            with gr.Column(scale=1):
                gr.Markdown("### Take Action")

                file_path = gr.Textbox(
                    label="FILE PATH",
                    placeholder="e.g. README.md or src/dataflow/loader.py",
                )
                file_content = gr.Textbox(
                    label="FILE CONTENT",
                    placeholder="# DataFlow\n\n## Installation\n\npip install dataflow\n\n## Usage\n...",
                    lines=10,
                )
                done_checkbox = gr.Checkbox(label="Mark as Done (finish early)", value=False)
                step_btn = gr.Button("Submit Step", variant="primary", size="lg")

        # ─── Collapsible Details ───
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Project Files", open=False):
                    files_display = gr.DataFrame(
                        headers=["File", "Size"],
                        datatype=["str", "str"],
                        value=[["—", "—"]],
                        interactive=False,
                    )

                with gr.Accordion("Raw JSON Response", open=False):
                    raw_json = gr.Code(label="Response", language="json", value="")

        # ─── Grade All Tasks Panel ───
        with gr.Accordion("Grade All Tasks (runs grader on current project)", open=False, visible=True) as grade_panel:
            grade_output = gr.JSON(label="Grading Results", value={})

        # ─── Handlers ───

        async def on_reset(task_id):
            try:
                result = await web_manager.reset_environment(task_id=task_id)
                obs = result.get("observation", result)

                score = obs.get("score", 0.0)
                steps = obs.get("steps_remaining", 7)
                breakdown = obs.get("score_breakdown", {})
                feedback_list = obs.get("feedback", [])
                project_files = obs.get("project_files", {})
                task_id_resp = obs.get("task_id", task_id)

                feedback_md = ""
                if feedback_list:
                    for fb in feedback_list:
                        feedback_md += f"- {fb}\n"
                else:
                    feedback_md = "All checks passing!"

                breakdown_table = [[k, round(v, 4)] for k, v in breakdown.items()]
                if not breakdown_table:
                    breakdown_table = [["—", 0.0]]

                file_table = [[k, f"{len(v)} chars"] for k, v in sorted(project_files.items())]
                if not file_table:
                    file_table = [["—", "—"]]

                return (
                    f"{score:.2f} / 1.00",
                    "—",
                    str(steps),
                    f"Active ({task_id_resp})",
                    feedback_md,
                    breakdown_table,
                    file_table,
                    json.dumps(result, indent=2, default=str),
                    True,
                )
            except Exception as e:
                return ("Error", "—", "—", "Error", f"**Error:** {e}",
                        [["—", 0.0]], [["—", "—"]], str(e), False)

        async def on_step(path, content, done, active):
            if not active:
                return (
                    "—", "—", "—", "Not started",
                    "**Click Reset first to start an episode**",
                    [["—", 0.0]], [["—", "—"]], "", False
                )

            if not path.strip():
                return (
                    "—", "—", "—", "Active",
                    "**Enter a file path before submitting**",
                    [["—", 0.0]], [["—", "—"]], "", active
                )

            try:
                action_data = {"files": {path.strip(): content}, "done": done}
                result = await web_manager.step_environment(action_data)
                obs = result.get("observation", result)

                score = obs.get("score", 0.0)
                steps = obs.get("steps_remaining", 0)
                reward = result.get("reward", 0.0)
                breakdown = obs.get("score_breakdown", {})
                feedback_list = obs.get("feedback", [])
                is_done = result.get("done", False)
                project_files = obs.get("project_files", {})

                feedback_md = ""
                if is_done:
                    feedback_md += f"**Episode Complete! Final score: {score:.4f}**\n\n"
                if feedback_list:
                    for fb in feedback_list:
                        feedback_md += f"- {fb}\n"
                else:
                    feedback_md += "All checks passing!"

                breakdown_table = [[k, round(v, 4)] for k, v in breakdown.items()]
                if not breakdown_table:
                    breakdown_table = [["—", 0.0]]

                file_table = [[k, f"{len(v)} chars"] for k, v in sorted(project_files.items())]
                if not file_table:
                    file_table = [["—", "—"]]

                reward_str = f"{reward:+.4f}" if reward is not None else "0.0"
                status = "Complete" if is_done else "Active"

                return (
                    f"{score:.2f} / 1.00",
                    reward_str,
                    str(steps),
                    status,
                    feedback_md,
                    breakdown_table,
                    file_table,
                    json.dumps(result, indent=2, default=str),
                    not is_done,
                )
            except Exception as e:
                return ("Error", "—", "—", "Error", f"**Error:** {e}",
                        [["—", 0.0]], [["—", "—"]], str(e), active)

        async def on_grade():
            try:
                from .grading import grade_project
                from .environment import AuditorEnvironment
                env = AuditorEnvironment()
                files = env._load_sample_project()
                results = {}
                for task in ["easy", "medium", "hard"]:
                    r = grade_project(files, task)
                    results[task] = {"score": r.score, "breakdown": r.breakdown}
                return results
            except Exception as e:
                return {"error": str(e)}

        reset_btn.click(
            fn=on_reset,
            inputs=[task_selector],
            outputs=[score_display, reward_display, steps_display, episode_status,
                     feedback_display, breakdown_display, files_display, raw_json,
                     episode_active],
        )

        step_btn.click(
            fn=on_step,
            inputs=[file_path, file_content, done_checkbox, episode_active],
            outputs=[score_display, reward_display, steps_display, episode_status,
                     feedback_display, breakdown_display, files_display, raw_json,
                     episode_active],
        )

        grade_btn.click(
            fn=on_grade,
            outputs=[grade_output],
        )

    return demo
