"""FastAPI application for the AI-Readiness Auditor environment."""
from openenv.core.env_server import create_app
from ai_readiness_auditor.server.environment import AuditorEnvironment
from ai_readiness_auditor.models import AuditorAction, AuditorObservation

app = create_app(
    env=AuditorEnvironment,
    action_cls=AuditorAction,
    observation_cls=AuditorObservation,
    env_name="ai_readiness_auditor",
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
