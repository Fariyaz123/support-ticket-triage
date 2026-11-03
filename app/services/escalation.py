from app.config import Settings
from app.schemas import ClassificationResult, ValidationResult


SENSITIVE_INTENTS = {
    "refund_request",
    "payment_issue",
    "duplicate_charge",
    "account_cancellation",
    "security_incident",
    "privacy_request",
    "legal_question",
    "complaint",
}


def decide_review(
    classification: ClassificationResult,
    validation: ValidationResult,
    max_retrieval_score: float,
    settings: Settings,
) -> tuple[bool, str | None]:
    if classification.intent in SENSITIVE_INTENTS:
        return True, "sensitive_case"
    if classification.urgency == "critical":
        return True, "critical_urgency"
    if classification.confidence < settings.classification_confidence_threshold:
        return True, "low_classification_confidence"
    if max_retrieval_score < settings.retrieval_score_threshold:
        return True, "no_relevant_faq"
    if validation.confidence < settings.validation_confidence_threshold:
        return True, "low_answer_confidence"
    if not validation.supported:
        return True, "unsupported_answer"
    return False, None

