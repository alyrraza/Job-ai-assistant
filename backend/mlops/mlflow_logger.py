# Logs every agent run's data with MLflow.
# Per experiment: input size, output score, retry count, latency — everything is tracked.
# Saved to the local mlruns/ folder — no cloud needed.

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator, Optional

import mlflow
from mlflow.entities import Run

from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()


class MLflowLogger:
    """Wrapper around MLflow — a clean API for agent runs."""

    def __init__(self) -> None:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        logger.info(
            f"MLflow tracking URI: {settings.mlflow_tracking_uri} | "
            f"Experiment: {settings.mlflow_experiment_name}"
        )

    @contextmanager
    def start_run(
        self,
        run_name: str,
        tags: Optional[dict[str, str]] = None,
    ) -> Generator[Run, None, None]:
        """Context manager — start a run, do the work, end it automatically."""
        _tags = tags or {}
        with mlflow.start_run(run_name=run_name, tags=_tags) as run:
            logger.debug(f"MLflow run started: {run_name} (id={run.info.run_id})")
            yield run
            logger.debug(f"MLflow run ended: {run_name} (id={run.info.run_id})")

    def log_agent_run(
        self,
        agent_name: str,
        session_id: str,
        attempt: int,
        status: str,
        params: dict[str, Any],
        metrics: dict[str, float],
        tags: Optional[dict[str, str]] = None,
    ) -> str:
        """Save the full record of one agent run and return the run_id."""
        _tags = {
            "agent": agent_name,
            "session_id": session_id,
            "attempt": str(attempt),
            "status": status,
            **(tags or {}),
        }
        with mlflow.start_run(run_name=f"{agent_name}_attempt_{attempt}", tags=_tags) as run:
            mlflow.log_params(self._flatten(params))
            mlflow.log_metrics(metrics)
            return run.info.run_id

    def log_params(self, params: dict[str, Any]) -> None:
        """Log params to the active run."""
        mlflow.log_params(self._flatten(params))

    def log_metrics(self, metrics: dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics to the active run."""
        mlflow.log_metrics(metrics, step=step)

    def log_artifact_text(self, content: str, filename: str) -> None:
        """Save string content as an artifact."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=f"_{filename}", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            mlflow.log_artifact(tmp_path, artifact_path="outputs")
        finally:
            os.unlink(tmp_path)

    @staticmethod
    def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, str]:
        """Flatten a nested dict into flat string keys for MLflow."""
        result: dict[str, str] = {}
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(MLflowLogger._flatten(v, full_key))
            else:
                result[full_key] = str(v)[:250]  # MLflow param limit
        return result


def timed_block(logger_instance: MLflowLogger, metric_name: str = "duration_seconds"):
    """Decorator — measure a function's runtime and log it to MLflow."""
    def decorator(fn):
        import functools

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - start
            try:
                logger_instance.log_metrics({metric_name: elapsed})
            except Exception:
                pass
            return result

        return wrapper
    return decorator


# Module-level singleton
mlflow_logger = MLflowLogger()
