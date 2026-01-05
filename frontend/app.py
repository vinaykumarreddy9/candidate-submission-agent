"""
Streamlit Frontend - DIGOT AI Recruitment Orchestrator

Provides an interactive dashboard for recruiters to:
- Upload candidate resumes (PDF format)
- Input job descriptions
- Review AI-generated candidate evaluations
- Approve or reject outreach emails (Human-in-the-Loop)

The UI maintains session state to support multi-step approval workflows.
"""

import streamlit as st
import requests
import os
import json
from dotenv import load_dotenv

# Load global configuration
load_dotenv()

# --- CONFIGURATION ---
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINT = "/api/v1/recruitment/execute"
APPROVE_ENDPOINT = "/api/v1/recruitment/approve"

# Professional headers to prevent bot-detection blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# --- SESSION STATE INITIALIZATION ---
if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None
if 'pending_approval' not in st.session_state:
    st.session_state.pending_approval = False

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="DIGOT AI | Recruitment Orchestrator",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN DESIGN SYSTEM (CSS) ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .stTextArea textarea {
        background-color: #1a1c23;
        color: #ffffff;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
    }
    .info-card {
        background-color: #161b22;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #30363d;
        margin-bottom: 1rem;
    }
    .match-header {
        color: #10b981;
        font-size: 1.2rem;
        font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SERVICE STATUS ---
st.sidebar.title("System Status")
backend_url_input = st.sidebar.text_input("Backend Service URL", value=DEFAULT_BACKEND_URL)
st.sidebar.divider()
st.sidebar.markdown("""
**Current Pipeline Version**: 1.0.0  
**Engine**: Llama-3.3-70B (Groq)  
**Status**: [Connected]
""")
st.title("💼 DIGOT AI Recruitment Orchestrator")
st.markdown("##### High-fidelity candidate generation, screening, and outreach automation.")

# --- CHAT INTERFACE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Paste Job Description and generation requirements (e.g. Generate 5 Senior devs...)"):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process workflow
    with st.chat_message("assistant"):
        with st.spinner("Analyzing query and generating candidates..."):
            try:
                # Construct Execution Payload
                payload = {"user_query": prompt}
                
                # API Request
                api_call_url = f"{backend_url_input}{API_ENDPOINT}"
                response = requests.post(api_call_url, json=payload, headers=HEADERS, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.workflow_result = result
                    st.session_state.pending_approval = True
                    
                    # Results are auto-displayed in the Dashboard below
                    pass
                else:
                    st.error(f"Upstream Service Error ({response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"Network Connectivity Failure: {str(e)}")

# --- RESULTS & APPROVAL DASHBOARD ---
if st.session_state.workflow_result:
    workflow_result = st.session_state.workflow_result
    
    # --- PIPELINE METRICS ---
    st.markdown("### 📊 Pipeline Performance Metrics")
    m1, m2 = st.columns(2)
    with m1:
        st.metric(label="Profiles Created", value=workflow_result.get('total_processed', 0))
    with m2:
        st.metric(label="Technical Matches", value=workflow_result.get('matched_count', 0))
    st.divider()
    
    # Match Analysis Detail
    with st.expander("🔍 View Technical Match Analysis", expanded=True):
        qualified_matches = workflow_result.get("qualified_matches", [])
        if qualified_matches:
            for match in qualified_matches:
                st.markdown(f"""
                <div class="info-card">
                    <div class="match-header">{match['candidate_name']}</div>
                    <p style="margin-top: 0.5rem;"><b>Score</b>: {match['screening_score']}/100</p>
                    <p><b>Technical Audit</b>: {match['evaluation_reasoning']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No candidates bypassed the strict technical threshold (Score < 85).")
            
    # Outreach Draft Preview & Approval
    if workflow_result.get("outreach_email_draft"):
        with st.expander("📧 Generated Outreach Proposal", expanded=True):
            target_email = workflow_result.get("target_contact_email", "")
            
            # Allow manual email entry if extraction failed or needs adjustment
            st.markdown("##### 📮 Recipient Information")
            recipient_email = st.text_input(
                "Target Recipient Email", 
                value=target_email if "@" in str(target_email) else "",
                placeholder="recruiter@example.com",
                help="We extracted this from the JD. You can correct it here if needed."
            )
            
            if not recipient_email:
                st.warning("Please provide a valid recipient email to proceed with outreach.")
            
            st.markdown("---")
            st.markdown("##### 📝 Email Draft Preview")
            st.code(workflow_result.get("outreach_email_draft"), language="markdown")
            
            if st.session_state.pending_approval:
                st.warning("⚠️ **Human-in-the-Loop Confirmation Required**")
                col_acc, col_rej = st.columns([1, 1])
                
                # Disable send if email is missing
                can_send = "@" in str(recipient_email)
                
                if col_acc.button("✅ APPROVE & SEND EMAIL", disabled=not can_send):
                    with st.spinner("Dispatching outreach via SMTP..."):
                        try:
                            # Update the state with the corrected email
                            full_state = workflow_result.get("full_state", {})
                            full_state["target_contact_email"] = recipient_email
                            
                            approve_payload = {"state": full_state}
                            approve_url = f"{backend_url_input}{APPROVE_ENDPOINT}"
                            res = requests.post(approve_url, json=approve_payload, headers=HEADERS)
                            
                            if res.status_code == 200:
                                st.session_state.workflow_result = res.json()
                                st.session_state.pending_approval = False
                                st.success("Email Delivered Successfully!")
                                st.rerun()
                            else:
                                st.error(f"Approval Failed: {res.text}")
                        except Exception as e:
                            st.error(f"Approval Error: {e}")
                
                if col_rej.button("❌ REJECT & ABANDON"):
                    st.session_state.workflow_result = None
                    st.session_state.pending_approval = False
                    st.info("Workflow execution cleared.")
                    st.rerun()
            elif workflow_result.get("outreach_email_status") == "Delivered":
                st.success(f"✅ This outreach has been delivered to {recipient_email}.")
            else:
                status = workflow_result.get("outreach_email_status", "Unknown")
                st.info(f"ℹ️ Status: {status}")

st.divider()
st.caption("Powered by DIGOT AI | Orchestrated with LangGraph & Groq")
