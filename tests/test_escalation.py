from app.config import Settings
from app.schemas import ClassificationResult, ValidationResult
from app.services.escalation import decide_review


def classification(intent="general_question", urgency="low", confidence=0.95):
    return ClassificationResult(category="other", urgency=urgency, intent=intent, confidence=confidence, summary="A support request")


def validation(supported=True, confidence=0.95):
    return ValidationResult(supported=supported, confidence=confidence, unsupported_claims=[])


def test_refund_always_requires_human_review():
    review, reason = decide_review(classification(intent="refund_request"), validation(), 0.9, Settings())
    assert review is True
    assert reason == "sensitive_case"


def test_low_retrieval_score_requires_human_review():
    review, reason = decide_review(classification(), validation(), 0.1, Settings())
    assert review is True
    assert reason == "no_relevant_faq"


def test_grounded_safe_ticket_can_be_answered():
    review, reason = decide_review(classification(), validation(), 0.8, Settings())
    assert review is False
    assert reason is None


def test_unsupported_answer_requires_human_review():
    review, reason = decide_review(classification(), validation(supported=False), 0.8, Settings())
    assert review is True
    assert reason == "unsupported_answer"

