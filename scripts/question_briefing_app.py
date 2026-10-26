"""Explicit opt-in composition root; API and worker meet only here."""

import os

from issuedigest_agents.question_submission import QuestionSubmissionError
from issuedigest_api.auth_config import RuntimeConfigurationError
from issuedigest_api.main import IssueDigestAPI
from issuedigest_api.runtime import create_configured_app
from issuedigest_worker.question_service import OwnedQuestionExecutionService, QuestionServiceConfig


def create_question_briefing_app() -> IssueDigestAPI:
    failed = False
    try:
        config = QuestionServiceConfig.from_environment(os.environ)
    except QuestionSubmissionError:
        failed = True
    if failed:
        raise RuntimeConfigurationError()
    return create_configured_app(
        service_factory=lambda engine: OwnedQuestionExecutionService(engine, config)
    )
