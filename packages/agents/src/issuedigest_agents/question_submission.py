"""Application-independent async execution boundary; no runtime ownership here."""

from typing import Protocol
from uuid import UUID

from issuedigest_domain.question_submission import QuestionErrorKind, QuestionSubmissionResult


class QuestionSubmissionError(Exception):
    """Only a known fixed category may cross the HTTP boundary."""

    def __init__(self, kind: QuestionErrorKind) -> None:
        if kind not in {"unauthorized", "forbidden", "conflict", "budget", "unavailable"}:
            kind = "unavailable"
        self.kind = kind
        super().__init__("Question submission failed")


class QuestionExecutionService(Protocol):
    async def start(self) -> None: ...
    async def aclose(self) -> None: ...
    async def authorize(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> bool: ...
    async def run(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> QuestionSubmissionResult: ...
