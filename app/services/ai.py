from app.config import Settings
from app.schemas import ClassificationResult, ValidationResult
from app.services.knowledge import RetrievedDocument


class AIService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = None
        if not settings.use_mock_ai and settings.openai_api_key:
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(model=settings.openai_model, temperature=0, api_key=settings.openai_api_key)

    def classify(self, subject: str, description: str) -> ClassificationResult:
        if self.llm is not None:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                Classify a support ticket. Allowed categories are billing,
                login_access, technical_issue, refund, account_management, or other.
                Allowed urgency values are low, medium, high, or critical.
                Return category, urgency, intent, confidence from 0 to 1, and a short summary.
                A refund, payment, security, privacy, legal, cancellation, or complaint intent
                must be explicit in the intent field.
                """),
                ("human", "Subject: {subject}\nDescription: {description}"),
            ])
            return (prompt | self.llm.with_structured_output(ClassificationResult)).invoke({"subject": subject, "description": description})
        return self._mock_classify(subject, description)

    def generate_answer(self, subject: str, description: str, documents: list[RetrievedDocument]) -> str:
        context = "\n\n".join(f"[{doc.source_name} / {doc.section}]\n{doc.content}" for doc in documents)
        if self.llm is not None:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                ("system", "Answer only from the supplied support knowledge. Do not invent prices, timelines, approvals, or policy. If the context is insufficient, say that a support agent needs to review the request. Keep the response concise and professional."),
                ("human", "Ticket subject: {subject}\nTicket description: {description}\n\nKnowledge context:\n{context}"),
            ])
            return self.llm.invoke(prompt.format_messages(subject=subject, description=description, context=context)).content

        if not documents:
            return "A support agent needs to review this request because no verified FAQ guidance was found."
        return f"We received your request about {subject.lower()}. Based on our support guidance:\n\n{documents[0].content}\n\nIf this does not resolve the issue, a support agent will review it."

    def validate_answer(self, answer: str, documents: list[RetrievedDocument]) -> ValidationResult:
        context = "\n\n".join(doc.content for doc in documents)
        if self.llm is not None:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages([
                ("system", "Determine whether every factual claim in the answer is supported by the context. Return supported, confidence from 0 to 1, and unsupported_claims."),
                ("human", "Context:\n{context}\n\nAnswer:\n{answer}"),
            ])
            return (prompt | self.llm.with_structured_output(ValidationResult)).invoke({"context": context, "answer": answer})
        if not documents:
            return ValidationResult(supported=False, confidence=0.25, unsupported_claims=["No source context was retrieved"])
        return ValidationResult(supported=True, confidence=0.90, unsupported_claims=[])

    @staticmethod
    def _mock_classify(subject: str, description: str) -> ClassificationResult:
        text = f"{subject} {description}".lower()
        if any(word in text for word in ("refund", "charged twice", "duplicate charge", "payment")):
            category, intent, urgency = "billing", ("duplicate_charge" if "twice" in text or "duplicate" in text else "refund_request"), "high"
        elif any(word in text for word in ("security breach", "hacked", "data leak")):
            category, intent, urgency = "technical_issue", "security_incident", "critical"
        elif any(word in text for word in ("password", "login", "sign in", "reset link")):
            category, intent, urgency = "login_access", "password_reset", "medium"
        elif any(word in text for word in ("cancel", "close my account")):
            category, intent, urgency = "account_management", "account_cancellation", "high"
        elif any(word in text for word in ("crash", "error", "not working", "bug")):
            category, intent, urgency = "technical_issue", "technical_problem", "high"
        else:
            category, intent, urgency = "other", "general_question", "low"
        return ClassificationResult(category=category, urgency=urgency, intent=intent, confidence=0.93, summary=f"Customer needs help with {intent.replace('_', ' ')}.")

