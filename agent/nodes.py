"""
Agent Processing Nodes - DIGOT AI Recruitment Orchestrator

This module contains all specialized agent nodes that form the recruitment pipeline:
- evaluate_candidates_node: Technical screening and scoring
- generate_outreach_node: Email drafting for qualified candidates
- deliver_outreach_node: SMTP transmission after HITL approval
- supervisor_node: Central orchestration and routing logic

Each node is designed to be stateless and communicates via WorkflowState.
"""

import os
import smtplib
import traceback
from email.mime.text import MIMEText
from typing import List, Dict, Any
from dotenv import load_dotenv

# LangChain & AI Infrastructure
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Internal Domain Logic
from agent.state import WorkflowState, CandidateEvaluation
from agent.prompts import (
    PROMPT_BATCH_CANDIDATE_SCREENING,
    PROMPT_EMAIL_EXTRACTION,
    PROMPT_OUTREACH_DRAFTING,
    PROMPT_RECRUITMENT_SUPERVISOR
)

# Load environment configuration
load_dotenv()

# --- INFRASTRUCTURE: INFERENCE ENGINE ---
try:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("CRITICAL: GROQ_API_KEY is missing from environment.")
    
    # Initialize Llama 3.3 via Groq for ultra-low latency
    language_model = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=GROQ_API_KEY,
        temperature=0.1,
        max_retries=2
    )
except Exception as e:
    print(f"Failed to initialize Inference Engine: {e}")
    language_model = None

# --- MODELS: STRUCTURED OUTPUT SCHEMAS ---
class CandidateScreeningResult(BaseModel):
    """Schema for individual candidate screening results from the LLM."""
    name: str = Field(description="Full name of the candidate")
    score: int = Field(description="Technical alignment score (0-100)")
    is_match: bool = Field(description="Match status (True if score >= 85)")
    reasoning: str = Field(description="Strict strengths and gaps assessment")

# --- WORKFLOW NODE: CANDIDATE EVALUATION ---
async def evaluate_candidates_node(state: WorkflowState) -> WorkflowState:
    """
    CRITICAL NODE: Orchestrates the batch screening of candidate resumes.
    
    This node extracts raw text from the state, formats it for the LLM, 
    and performs a technical cross-analysis against the Job Description.
    """
    print("--- [NODE: EVALUATE CANDIDATES] Starting Batch Technical Screening ---")
    try:
        job_description = state.get("job_description", "")
        raw_profiles = state.get("raw_candidate_profiles", [])
        
        # Defensive check for empty input
        if not raw_profiles or not job_description:
            print("Warning: Missing input data for evaluation.")
            return {"processed_evaluations": [], "qualified_matches": []}

        if not language_model:
            raise RuntimeError("Inference engine is offline.")

        # Batch candidate profiles into a single context for efficiency
        formatted_profiles = "\n\n".join([f"--- Candidate {i+1} ---\n{p}" for i, p in enumerate(raw_profiles)])
        
        # Configure the screening chain
        screening_prompt = PromptTemplate.from_template(PROMPT_BATCH_CANDIDATE_SCREENING)
        response_parser = JsonOutputParser()
        screening_chain = screening_prompt | language_model | response_parser
        
        # Execute batch screening asynchronously
        raw_llm_results = await screening_chain.ainvoke({
            "job_description": job_description, 
            "formatted_profiles": formatted_profiles
        })
        
        # Robust parsing: Ensure results are handled as a list of dicts
        if isinstance(raw_llm_results, dict) and "candidates" in raw_llm_results:
            # Handle possible nested JSON structures if LLM deviates
            results_list = raw_llm_results["candidates"]
        else:
            results_list = raw_llm_results if isinstance(raw_llm_results, list) else [raw_llm_results]

        processed_evaluations = []
        qualified_matches = []
        
        # Map raw LLM output to standardized domain entities
        for idx, result in enumerate(results_list):
            evaluation: CandidateEvaluation = {
                "candidate_id": idx,
                "candidate_name": result.get("name", f"Candidate {idx+1}"),
                "screening_score": int(result.get("score", 0)) if str(result.get("score", 0)).isdigit() else 0,
                "is_technical_match": bool(result.get("is_match", False)),
                "evaluation_reasoning": result.get("reasoning", "No evaluation details provided."),
                "original_profile_text": raw_profiles[idx] if idx < len(raw_profiles) else ""
            }
            processed_evaluations.append(evaluation)
            if evaluation["is_technical_match"]:
                qualified_matches.append(evaluation)
                
        return {
            "processed_evaluations": processed_evaluations,
            "qualified_matches": qualified_matches
        }
        
    except Exception as e:
        print(f"Workflow Fault in Evaluation Node:\n{traceback.format_exc()}")
        return {
            "processed_evaluations": [{
                "candidate_id": 0,
                "candidate_name": "System Failure",
                "screening_score": 0,
                "is_technical_match": False,
                "evaluation_reasoning": f"Fault Details: {str(e)}",
                "original_profile_text": ""
            }],
            "qualified_matches": []
        }

# --- WORKFLOW NODE: OUTREACH GENERATION ---
async def generate_outreach_node(state: WorkflowState) -> WorkflowState:
    """
    DRAFTING NODE: Synthesizes personalized outreach for top-tier candidates.
    
    This node identifies the target contact and drafts a persuasive proposal.
    It does NOT send the email; it marks state for HITL approval.
    """
    print("--- [NODE: GENERATE OUTREACH] Drafting Personalized Proposals ---")
    try:
        job_description = state.get("job_description", "")
        qualified_matches = state.get("qualified_matches", [])
        
        # Graceful skip if no candidates passed the screening threshold
        if not qualified_matches:
            return {
                "target_contact_email": "",
                "generated_email_draft": "No qualified matches identified for outreach.",
                "email_delivery_status": "Skipped"
            }

        if not language_model:
            raise RuntimeError("Inference engine is offline.")
            
        # TASK 1: Extract Primary Contact Information
        try:
            extraction_prompt = PromptTemplate.from_template(PROMPT_EMAIL_EXTRACTION)
            extraction_chain = extraction_prompt | language_model
            extraction_res = await extraction_chain.ainvoke({"job_description": job_description})
            target_email = extraction_res.content.strip() if hasattr(extraction_res, 'content') else str(extraction_res)
            if "@" not in target_email:
                target_email = ""
        except Exception as e:
            print(f"Contact Extraction Fault: {e}")
            target_email = ""
        
        # TASK 2: Synthesize Personalized Outreach Proposal
        try:
            # Construction of summary block for the LLM
            summaries = "\n\n".join([
                f"- {c['candidate_name']} (Final Score: {c['screening_score']}/100): {c['evaluation_reasoning']}" 
                for c in qualified_matches
            ])
            
            drafting_prompt = PromptTemplate.from_template(PROMPT_OUTREACH_DRAFTING)
            drafting_chain = drafting_prompt | language_model
            draft_res = await drafting_chain.ainvoke({
                "contact_email": target_email or "Hiring Team", 
                "job_description": job_description,
                "candidate_summaries": summaries
            })
            email_body = draft_res.content if hasattr(draft_res, 'content') else str(draft_res)
        except Exception as e:
            print(f"Drafting Fault: {e}")
            email_body = "Automated drafting failed. Manual intervention required."
        
        return {
            "target_contact_email": target_email,
            "generated_email_draft": email_body,
            "email_delivery_status": "Drafted - Pending Approval"
        }
    except Exception as e:
        print(f"Workflow Fault in Outreach Node:\n{traceback.format_exc()}")
        return {
            "target_contact_email": "",
            "generated_email_draft": "Orchestration failure during drafting phase.",
            "email_delivery_status": "Failed"
        }

# --- WORKFLOW NODE: EMAIL TRANSMISSION ---
async def deliver_outreach_node(state: WorkflowState) -> WorkflowState:
    """
    TRANSMISSION NODE: Executes actual email delivery after HITL approval.
    
    This node verifies human approval, validates metadata, and orchestrates
    SMTP transmission. It will NOT execute without explicit user consent.
    """
    print("--- [NODE: DELIVER OUTREACH] Initiating Email Transmission ---")
    try:
        target_email = state.get("target_contact_email", "")
        email_body = state.get("generated_email_draft", "")
        is_approved = state.get("is_approved", False)

        # CRITICAL: Block execution if approval is not granted
        if not is_approved:
            print("⚠️ Transmission blocked: Awaiting human approval.")
            return {"email_delivery_status": "Blocked: Awaiting Human Approval"}

        # Validate transmission metadata
        if not target_email or not email_body:
            print("❌ Transmission failed: Missing email metadata.")
            return {"email_delivery_status": "Failed: Missing metadata for transmission"}

        # Orchestrate SMTP Delivery
        delivery_report = execute_smtp_transmission(
            recipient=target_email, 
            subject="Qualified Technical Matches - DIGOT AI Recruitment Analysis", 
            body=email_body
        )

        print(f"✅ Email transmission complete: {delivery_report}")
        # CRITICAL: Reset approval flag to prevent infinite loop
        return {
            "email_delivery_status": delivery_report,
            "is_approved": False
        }

    except Exception as e:
        print(f"Transmission Fault: {e}")
        return {"email_delivery_status": f"System Error: {str(e)}"}

# --- UTILITY: SMTP TRANSMISSION ENGINE ---
def execute_smtp_transmission(recipient: str, subject: str, body: str) -> str:
    """Executes secure email transmission via configured SMTP gateway."""
    gateway_address = os.getenv("SMTP_SERVER")
    gateway_port = os.getenv("SMTP_PORT")
    auth_user = os.getenv("SENDER_EMAIL")
    auth_pass = os.getenv("SMTP_PASSWORD")
    
    # Metadata validation before connection attempt
    if not all([gateway_address, gateway_port, auth_user, auth_pass]):
        return "Simulation: Dispatch metadata valid but credentials missing."
        
    try:
        email_message = MIMEText(body)
        email_message['Subject'] = subject
        email_message['From'] = f"DIGOT AI Partner <{auth_user}>"
        email_message['To'] = recipient
        
        with smtplib.SMTP(gateway_address, int(gateway_port), timeout=10) as connection:
            connection.starttls()
            connection.login(auth_user, auth_pass)
            connection.send_message(email_message)
        return "Delivered"
    except Exception as e:
        return f"Transmission Failure: {str(e)}"

# --- WORKFLOW NODE: SUPERVISOR ---
async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """
    ORCHESTRATION SUPERVISOR: The central intelligence that routes workflow execution.
    
    This node analyzes the current state and decides which specialized agent
    should execute next. It implements both LLM-driven and rule-based routing
    for maximum reliability.
    """
    print("--- [NODE: SUPERVISOR] Analyzing State & Routing Workflow ---")
    try:
        if not language_model:
            raise RuntimeError("Inference engine is offline.")

        # Prepare context for the supervisor
        has_evaluations = len(state.get("processed_evaluations", [])) > 0
        has_outreach = len(state.get("generated_email_draft", "")) > 0
        match_count = len(state.get("qualified_matches", []))
        is_approved = state.get("is_approved", False)

        supervisor_prompt = PromptTemplate.from_template(PROMPT_RECRUITMENT_SUPERVISOR)
        supervisor_chain = supervisor_prompt | language_model
        
        response = await supervisor_chain.ainvoke({
            "has_evaluations": "Yes" if has_evaluations else "No",
            "has_outreach": "Yes" if has_outreach else "No",
            "match_count": match_count,
            "is_approved": "Yes" if is_approved else "No"
        })

        next_agent = response.content.strip()
        
        print(f"🤖 Supervisor Decision (LLM): {next_agent}")
        
        # Validation and fallback logic
        valid_agents = ["evaluate_candidates", "generate_outreach", "send_outreach", "FINISH"]
        if next_agent not in valid_agents:
            # Logic-based fallback if LLM deviates
            if not has_evaluations:
                next_agent = "evaluate_candidates"
            elif match_count > 0 and not has_outreach:
                next_agent = "generate_outreach"
            elif has_outreach and is_approved:
                next_agent = "send_outreach"
            else:
                next_agent = "FINISH"
        
        print(f"📍 Final Routing Decision: {next_agent}")
        return {"next_destination": next_agent}

    except Exception as e:
        print(f"Supervisor Fault: {e}")
        return {"next_destination": "FINISH"}
