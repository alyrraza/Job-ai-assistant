# Yeh file MLflow ke saath har agent run ka data log karti hai.
# Har experiment: input size, output score, retry count, latency — sab track hota hai.
# Local mlruns/ folder mein save hota hai — koi cloud nahi chahiye.

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
    """Wrapper around MLflow — agent runs ke liye clean API."""

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
        """Context manager — run start karo, kaam karo, automatically end ho jaaye."""
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
        """Ek agent run ka pura record save karo, run_id wapas lo."""
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
        """Active run mein params log karo."""
        mlflow.log_params(self._flatten(params))

    def log_metrics(self, metrics: dict[str, float], step: Optional[int] = None) -> None:
        """Active run mein metrics log karo."""
        mlflow.log_metrics(metrics, step=step)

    def log_artifact_text(self, content: str, filename: str) -> None:
        """String content ko artifact ke roop mein save karo."""
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
        """Nested dict ko flat string keys mein convert karo MLflow ke liye."""
        result: dict[str, str] = {}
        for k, v in d.items():
            full_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                result.update(MLflowLogger._flatten(v, full_key))
            else:
                result[full_key] = str(v)[:250]  # MLflow param limit
        return result


def timed_block(logger_instance: MLflowLogger, metric_name: str = "duration_seconds"):
    """Decorator — function ka runtime measure karo aur MLflow mein log karo."""
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
