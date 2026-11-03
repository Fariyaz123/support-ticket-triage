import os

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def api_request(method: str, path: str, **kwargs):
    response = requests.request(method, f"{API_BASE_URL}{path}", timeout=60, **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(detail)
    return response.json()


st.set_page_config(page_title="Support Ticket Triage", page_icon="🎫", layout="wide")
st.title("AI Support Ticket Triage Assistant")
page = st.sidebar.radio("Open", ["Submit ticket", "Track ticket", "Agent review"])

if page == "Submit ticket":
    st.header("Submit a support ticket")
    with st.form("ticket_form"):
        email = st.text_input("Email", "customer@example.com")
        subject = st.text_input("Subject")
        description = st.text_area("Describe the problem", height=180)
        attachment = st.file_uploader("Optional text attachment", type=["txt", "md", "log"])
        submitted = st.form_submit_button("Submit ticket")
    if submitted:
        try:
            result = api_request("POST", "/tickets", json={"customer_email": email, "subject": subject, "description": description, "attachment_name": attachment.name if attachment else None})
            st.success(f"Ticket {result['id']} was created.")
            st.json({"status": result["status"], "category": result.get("category"), "urgency": result.get("urgency"), "review_reason": result.get("review_reason")})
            if result.get("final_response"):
                st.info(result["final_response"])
            else:
                st.warning("This ticket was sent to a human support agent before a final response is sent.")
        except Exception as exc:
            st.error(str(exc))

elif page == "Track ticket":
    st.header("Track a ticket")
    ticket_number = st.text_input("Ticket ID")
    if st.button("Look up") and ticket_number:
        try:
            result = api_request("GET", f"/tickets/{ticket_number}")
            st.subheader(f"{result['id']} — {result['status']}")
            st.write(result.get("summary") or result["description"])
            st.json({"category": result.get("category"), "urgency": result.get("urgency"), "review_reason": result.get("review_reason")})
            if result.get("final_response"):
                st.info(result["final_response"])
            else:
                st.warning("A support agent is reviewing this ticket.")
        except Exception as exc:
            st.error(str(exc))

else:
    st.header("Human review queue")
    if st.button("Refresh queue") or "reviews" not in st.session_state:
        try:
            st.session_state.reviews = api_request("GET", "/reviews/pending")
        except Exception as exc:
            st.error(str(exc))
            st.session_state.reviews = []
    for ticket in st.session_state.get("reviews", []):
        with st.expander(f"{ticket['id']} — {ticket['subject']} — {ticket.get('review_reason')}"):
            st.write(ticket["description"])
            st.write(f"Category: `{ticket.get('category')}` | Urgency: `{ticket.get('urgency')}`")
            st.caption(f"AI draft: {ticket.get('draft_response')}")
            for source in ticket.get("sources", []):
                st.caption(f"Source: {source['source_name']} / {source['section']}")
            reviewer = st.text_input("Reviewer ID", "agent-1", key=f"reviewer-{ticket['id']}")
            edited = st.text_area("Final response (edit if needed)", ticket.get("draft_response") or "", key=f"response-{ticket['id']}")
            left, middle, right = st.columns(3)
            try:
                if left.button("Approve", key=f"approve-{ticket['id']}"):
                    api_request("POST", f"/reviews/{ticket['id']}", json={"reviewer_id": reviewer, "action": "approve"})
                    st.success("Approved")
                    st.rerun()
                if middle.button("Approve edited", key=f"edit-{ticket['id']}"):
                    api_request("POST", f"/reviews/{ticket['id']}", json={"reviewer_id": reviewer, "action": "edit", "edited_response": edited})
                    st.success("Edited response approved")
                    st.rerun()
                if right.button("Reject draft", key=f"reject-{ticket['id']}"):
                    api_request("POST", f"/reviews/{ticket['id']}", json={"reviewer_id": reviewer, "action": "reject", "comments": "Needs further investigation"})
                    st.warning("Draft rejected")
                    st.rerun()
            except Exception as exc:
                st.error(str(exc))
