# Yeh SABSE IMPORTANT file hai — sab agents isko inherit karte hain.
# Self-healing loop yahan implement hua hai: Execute → Validate → PASS/FAIL → Retry → Escalate.
# Har child agent sirf execute() aur validate() override kare — baaki sab free milta hai.

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from backend.mlops.mlflow_logger import mlflow_logger
from backend.utils.config import get_settings
from backend.utils.logger import logger

settings = get_settings()


class AgentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class AgentResult:
    """Har agent run ka structured output."""

    success: bool
    data: dict[str, Any]
    agent_name: str
    session_id: str
    attempt: int
    state: AgentState
    error: Optional[str] = None
    critique: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict."""
        return {
            "success": self.success,
            "data": self.data,
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "attempt": self.attempt,
            "state": self.state.value,
            "error": self.error,
            "critique": self.critique,
            "mlflow_run_id": self.mlflow_run_id,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """
    Abstract base — har agent yahan se inherit kare.

    Self-healing flow:
        run() → _execute_with_healing() → execute() → validate()
                                        ↓ fail
                                 self_critique() → retry (max 3)
                                        ↓ max retries
                                   escalate()
    """

    name: str = "base_agent"

    def __init__(self, session_id: Optional[str] = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self._attempt = 0
        self._state = AgentState.IDLE
        self._max_retries = settings.max_retries
        logger.info(f"[{self.name}] Initialized | session={self.session_id}")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Supervisor yahan call karta hai.
        Self-healing loop automatically handle hoti hai.
        """
        self._attempt = 0
        self._state = AgentState.RUNNING
        logger.info(f"[{self.name}] run() started | session={self.session_id}")
        return self._execute_with_healing(input_data)

    # ------------------------------------------------------------------
    # Self-healing core loop
    # ------------------------------------------------------------------

    def _execute_with_healing(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Execute → Validate → PASS  → return result
                           → FAIL  → self_critique → retry
                                   → max retries   → escalate
        """
        last_result: Optional[AgentResult] = None

        while self._attempt < self._max_retries:
            self._attempt += 1
            logger.info(
                f"[{self.name}] Attempt {self._attempt}/{self._max_retries} | session={self.session_id}"
            )

            start = time.perf_counter()
            try:
                raw_output = self.execute(input_data)
            except Exception as exc:
                duration = time.perf_counter() - start
                logger.error(
                    f"[{self.name}] execute() raised on attempt {self._attempt}: {exc}"
                )
                last_result = self._build_result(
                    success=False,
                    data={},
                    error=str(exc),
                    duration=duration,
                )
                input_data = self._inject_critique(input_data, last_result)
                continue

            duration = time.perf_counter() - start
            is_valid, validation_error = self.validate(raw_output)

            if is_valid:
                self._state = AgentState.PASSED
                result = self._build_result(
                    success=True,
                    data=raw_output,
                    duration=duration,
                )
                self._log_to_mlflow(input_data, result)
                logger.success(
                    f"[{self.name}] PASSED on attempt {self._attempt} | "
                    f"duration={duration:.2f}s | session={self.session_id}"
                )
                return result

            # Validation failed — self-critique
            logger.warning(
                f"[{self.name}] Validation FAILED attempt {self._attempt}: {validation_error}"
            )
            last_result = self._build_result(
                success=False,
                data=raw_output,
                error=validation_error,
                duration=duration,
            )
            input_data = self._inject_critique(input_data, last_result)

        # Max retries exhausted
        return self._do_escalate(input_data, last_result)

    # ------------------------------------------------------------------
    # Abstract methods — child must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Core agent logic — LLM call, processing, etc.
        Returns raw output dict (will be validated next).
        """

    @abstractmethod
    def validate(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Output check karo.
        Returns (True, None) on success, (False, "reason") on failure.
        """

    # ------------------------------------------------------------------
    # Self-critique — override for custom LLM-based critique
    # ------------------------------------------------------------------

    def self_critique(
        self,
        input_data: dict[str, Any],
        failed_output: dict[str, Any],
        error: Optional[str],
    ) -> str:
        """
        Failure ka reason analyze karo aur corrective hint banao.
        Override this in child agents for LLM-powered critique.
        """
        return (
            f"Attempt {self._attempt} failed: {error}. "
            f"Output keys present: {list(failed_output.keys())}. "
            "Please fix the output to match the required JSON schema."
        )

    # ------------------------------------------------------------------
    # Escalation — override to send to supervisor
    # ------------------------------------------------------------------

    def escalate(self, input_data: dict[str, Any], last_result: Optional[AgentResult]) -> None:
        """
        Max retries ke baad supervisor ko notify karo.
        Override to POST to /escalate endpoint.
        """
        logger.critical(
            f"[{self.name}] ESCALATED after {self._max_retries} attempts | session={self.session_id}"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _inject_critique(
        self, input_data: dict[str, Any], failed_result: AgentResult
    ) -> dict[str, Any]:
        """Critique generate karo aur next attempt ke liye input mein daal do."""
        critique = self.self_critique(
            input_data,
            failed_result.data,
            failed_result.error,
        )
        failed_result.critique = critique
        logger.debug(f"[{self.name}] Self-critique: {critique[:200]}")
        return {**input_data, "_critique": critique, "_attempt": self._attempt}

    def _do_escalate(
        self, input_data: dict[str, Any], last_result: Optional[AgentResult]
    ) -> AgentResult:
        self._state = AgentState.ESCALATED
        self.escalate(input_data, last_result)
        result = self._build_result(
            success=False,
            data=last_result.data if last_result else {},
            error=f"Escalated after {self._max_retries} failed attempts",
            duration=0.0,
        )
        result.state = AgentState.ESCALATED
        self._log_to_mlflow(input_data, result)
        return result

    def _build_result(
        self,
        success: bool,
        data: dict[str, Any],
        error: Optional[str] = None,
        duration: float = 0.0,
    ) -> AgentResult:
        return AgentResult(
            success=success,
            data=data,
            agent_name=self.name,
            session_id=self.session_id,
            attempt=self._attempt,
            state=self._state,
            error=error,
            duration_seconds=duration,
        )

    def _log_to_mlflow(self, input_data: dict[str, Any], result: AgentResult) -> None:
        """Result MLflow mein silently log karo — failure hone pe ignore karo."""
        try:
            run_id = mlflow_logger.log_agent_run(
                agent_name=self.name,
                session_id=self.session_id,
                attempt=self._attempt,
                status=result.state.value,
                params={
                    "max_retries": self._max_retries,
                    "input_keys": list(input_data.keys()),
                },
                metrics={
                    "duration_seconds": result.duration_seconds,
                    "attempt_number": float(self._attempt),
                    "success": 1.0 if result.success else 0.0,
                },
            )
            result.mlflow_run_id = run_id
        except Exception as exc:
            logger.warning(f"[{self.name}] MLflow logging failed (non-critical): {exc}")

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def attempt(self) -> int:
        return self._attempt
