"""Custom Gradio web interface for the AI-Readiness Auditor."""
import json
import gradio as gr


def build_ui(web_manager, action_fields, metadata, is_chat_env, title, quick_start_md):
    """Build a clean, judge-friendly web interface."""

    with gr.Blocks(title="AI-Readiness Auditor") as demo:

        # Header
        gr.Markdown(
            "# AI-Readiness Auditor\n"
            "An RL environment where AI agents improve a broken Python project for AI-readiness.\n\n"
            "**How it works:** Reset with a task → Submit file changes → Get score + feedback → Repeat"
        )

        # State
        episode_active = gr.State(False)

        with gr.Row():
            # Left column — Controls
            with gr.Column(scale=1):
                gr.Markdown("### Controls")

                task_selector = gr.Radio(
                    choices=["easy", "medium", "hard"],
                    value="easy",
                    label="Task Difficulty",
                    info="Easy: README + llms.txt | Medium: AI files + structure | Hard: Everything + code quality"
                )

                reset_btn = gr.Button("Reset Environment", variant="primary", size="lg")

                gr.Markdown("---")

                gr.Markdown("### Submit Files")
                file_path = gr.Textbox(
                    label="File Path",
                    placeholder="e.g. README.md",
                    info="Relative path of the file to create/update"
                )
                file_content = gr.Textbox(
                    label="File Content",
                    placeholder="# My Project\n\n## Installation\n...",
                    lines=8,
                    info="Full content of the file"
                )
                done_checkbox = gr.Checkbox(label="Mark as Done (finish early)", value=False)
                step_btn = gr.Button("Submit Step", variant="primary", size="lg")

            # Right column — Results
            with gr.Column(scale=2):
                gr.Markdown("### Environment State")

                with gr.Row():
                    score_display = gr.Textbox(label="Score", value="—", interactive=False)
                    steps_display = gr.Textbox(label="Steps Remaining", value="—", interactive=False)
                    reward_display = gr.Textbox(label="Last Reward", value="—", interactive=False)

                feedback_display = gr.Markdown("*Click Reset to start a new episode*", label="Feedback")

                gr.Markdown("### Score Breakdown")
                breakdown_display = gr.JSON(label="Per-Check Scores", value={})

                with gr.Accordion("Project Files", open=False):
                    files_display = gr.JSON(label="Current Files (path → content preview)", value={})

                with gr.Accordion("Raw JSON Response", open=False):
                    raw_json = gr.Code(label="Response", language="json", value="")

        # --- Handlers ---

        async def on_reset(task_id):
            try:
                result = await web_manager.reset_environment(task_id=task_id)
                obs = result.get("observation", result)

                score = obs.get("score", 0.0)
                steps = obs.get("steps_remaining", 7)
                breakdown = obs.get("score_breakdown", {})
                feedback = obs.get("feedback", [])
                project_files = obs.get("project_files", {})

                feedback_md = "### Feedback\n"
                if feedback:
                    for fb in feedback:
                        feedback_md += f"- {fb}\n"
                else:
                    feedback_md += "No issues found!"

                # Show file list with sizes
                file_summary = {k: f"{len(v)} chars" for k, v in project_files.items()}

                return (
                    f"{score:.4f}",
                    str(steps),
                    "—",
                    feedback_md,
                    breakdown,
                    file_summary,
                    json.dumps(result, indent=2, default=str),
                    True,
                )
            except Exception as e:
                return ("Error", "—", "—", f"**Error:** {e}", {}, {}, str(e), False)

        async def on_step(path, content, done, active):
            if not active:
                return (
                    "—", "—", "—",
                    "**Error:** Click Reset first to start an episode",
                    {}, {}, "", False
                )

            if not path.strip():
                return (
                    "—", "—", "—",
                    "**Error:** Enter a file path",
                    {}, {}, "", active
                )

            try:
                action_data = {"files": {path.strip(): content}, "done": done}
                result = await web_manager.step_environment(action_data)
                obs = result.get("observation", result)

                score = obs.get("score", 0.0)
                steps = obs.get("steps_remaining", 0)
                reward = result.get("reward", 0.0)
                breakdown = obs.get("score_breakdown", {})
                feedback = obs.get("feedback", [])
                is_done = result.get("done", False)
                project_files = obs.get("project_files", {})

                feedback_md = "### Feedback\n"
                if is_done:
                    feedback_md += f"**Episode Complete!** Final score: {score:.4f}\n\n"
                if feedback:
                    for fb in feedback:
                        feedback_md += f"- {fb}\n"
                else:
                    feedback_md += "All checks passing!"

                file_summary = {k: f"{len(v)} chars" for k, v in project_files.items()}

                reward_str = f"{reward:+.4f}" if reward is not None else "0.0"

                return (
                    f"{score:.4f}",
                    str(steps),
                    reward_str,
                    feedback_md,
                    breakdown,
                    file_summary,
                    json.dumps(result, indent=2, default=str),
                    not is_done,
                )
            except Exception as e:
                return ("Error", "—", "—", f"**Error:** {e}", {}, {}, str(e), active)

        reset_btn.click(
            fn=on_reset,
            inputs=[task_selector],
            outputs=[score_display, steps_display, reward_display, feedback_display,
                     breakdown_display, files_display, raw_json, episode_active],
        )

        step_btn.click(
            fn=on_step,
            inputs=[file_path, file_content, done_checkbox, episode_active],
            outputs=[score_display, steps_display, reward_display, feedback_display,
                     breakdown_display, files_display, raw_json, episode_active],
        )

    return demo
