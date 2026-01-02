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
import PyPDF2
import io
import re
from dotenv import load_dotenv

# Load global configuration
load_dotenv()

# --- CONFIGURATION ---
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINT = "/api/v1/recruitment/execute"
APPROVE_ENDPOINT = "/api/v1/recruitment/approve"

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

# --- UTILITY: PDF PROCESSING & TOKEN OPTIMIZATION ---
def clean_extracted_text(text):
    """
    Sanitizes extracted text to eliminate noise, excessive whitespace, 
    and non-essential characters for token efficiency.
    """
    if not text:
        return ""
    
    # 1. Normalize Whitespace: Remove multiple spaces and tabs
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 2. Normalize Newlines: Convert multiple newlines to double newlines (paragraphs)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    # 3. Noise Reduction: Remove non-printable/control characters that might be PDF artifacts
    text = "".join(char for char in text if char.isprintable() or char == '\n')
    
    # 4. Strip leading/trailing whitespace
    return text.strip()

def extract_text_from_pdf(pdf_file):
    """Extracts and sanitizes text from an uploaded PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        full_text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
        
        # Apply token optimization
        cleaned_text = clean_extracted_text(full_text)
        
        # Token Saving: Cap individual resume length to prevent context explosion 
        # (Standard resume text is rarely > 6000 chars)
        return cleaned_text[:8000] 
    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return ""

# --- MAIN INTERFACE ---
st.title("💼 DIGOT AI Recruitment Orchestrator")
st.markdown("##### High-fidelity candidate screening and outreach automation.")

col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("### 1. Job Context")
    job_description_text = st.text_area(
        "Paste Job Description here...",
        height=250,
        placeholder="e.g., We are seeking a Senior ML Engineer with expertise in Large Language Models..."
    )

with col_right:
    st.markdown("### 2. Candidate Pipeline")
    uploaded_files = st.file_uploader(
        "Upload Candidate Resumes (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can upload multiple resumes at once. The system will extract text and analyze each one."
    )
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} resumes uploaded successfully.")

st.divider()

# --- PIPELINE EXECUTION ---
if st.button("🚀 EXECUTE RECRUITMENT WORKFLOW"):
    if not job_description_text or not uploaded_files:
        st.warning("Action Required: Please provide both job context and upload candidate resumes.")
    else:
        with st.spinner("Processing PDF resumes and conducting AI analysis..."):
            # Extract text from all PDFs
            profile_list = []
            for pdf_file in uploaded_files:
                extracted_text = extract_text_from_pdf(pdf_file)
                if extracted_text:
                    profile_list.append(extracted_text)
            
            if not profile_list:
                st.error("Protocol Error: No text could be extracted from the uploaded PDFs.")
            else:
                try:
                    # Construct Execution Payload
                    payload = {
                        "job_description": job_description_text,
                        "candidate_profiles": profile_list
                    }
                    
                    # API Request
                    api_call_url = f"{backend_url_input}{API_ENDPOINT}"
                    response = requests.post(api_call_url, json=payload, timeout=60)
                    
                    if response.status_code == 200:
                        st.session_state.workflow_result = response.json()
                        st.session_state.pending_approval = True
                        st.success("Workflow Analysis Complete - Awaiting Human Approval")
                        st.rerun()
                    else:
                        st.error(f"Upstream Service Error ({response.status_code}): {response.text}")
                except Exception as e:
                    st.error(f"Network Connectivity Failure: {str(e)}")

# --- RESULTS & APPROVAL DASHBOARD ---
if st.session_state.workflow_result:
    workflow_result = st.session_state.workflow_result
    st.divider()
    
    # Metrics Overlay
    m_total, m_qualified, m_status = st.columns(3)
    m_total.metric("Candidates Screened", workflow_result.get("total_processed", 0))
    m_qualified.metric("Technical Matches", workflow_result.get("matched_count", 0))
    m_status.metric("Outreach Status", workflow_result.get("outreach_email_status", "N/A"))
    
    # Match Analysis Detail
    st.markdown("### 🏆 Qualified Candidate Analysis")
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
        st.markdown("### 📧 Generated Outreach Proposal")
        st.info(f"Target Recipient identified: **{workflow_result.get('target_contact_email', 'None')}**")
        st.code(workflow_result.get("outreach_email_draft"), language="markdown")
        
        if st.session_state.pending_approval and workflow_result.get("target_contact_email") != "None":
            st.warning("⚠️ **Human-in-the-Loop Confirmation Required**")
            col_acc, col_rej = st.columns([1, 1])
            
            if col_acc.button("✅ APPROVE & SEND EMAIL"):
                with st.spinner("Dispatching outreach via SMTP..."):
                    try:
                        approve_payload = {"state": workflow_result.get("full_state", {})}
                        approve_url = f"{backend_url_input}{APPROVE_ENDPOINT}"
                        res = requests.post(approve_url, json=approve_payload)
                        
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
            st.success("✅ This outreach has been delivered to the target recipient.")
        else:
            st.info("Outreach generation skipped or target email not found.")

st.divider()
st.caption("Powered by DIGOT AI | Orchestrated with LangGraph & Groq (Llama 3.3)")
