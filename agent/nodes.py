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
import json
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
    PROMPT_QUERY_ANALYSIS,
    PROMPT_CANDIDATE_GENERATION,
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
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        api_key=GROQ_API_KEY,
        temperature=0.1,
        max_retries=2
    )
except Exception as e:
    print(f"Failed to initialize Inference Engine: {e}")
    language_model = None

# --- MODELS: STRUCTURED OUTPUT SCHEMAS ---
class QueryAnalysisResult(BaseModel):
    """Schema for query analysis results."""
    job_description: str = Field(description="Extracted job description")
    generation_prompt: str = Field(description="Instructions for candidate generation")

class CandidateScreeningResult(BaseModel):
    """Schema for individual candidate screening results from the LLM."""
    name: str = Field(description="Full name of the candidate")
    score: int = Field(description="Technical alignment score (0-100)")
    is_match: bool = Field(description="Match status (True if score >= 85)")
    reasoning: str = Field(description="Strict strengths and gaps assessment")

# --- UTILITIES ---
def robust_bool(val: Any) -> bool:
    """Converts various types to boolean reliably."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1", "t", "y")
    return False

# --- WORKFLOW NODE: QUERY ANALYSIS ---
async def analyze_query_node(state: WorkflowState) -> WorkflowState:
    """
    ANALYZER NODE: Splits the single user input into JD and Generation Prompt.
    """
    print("--- [NODE: ANALYZE QUERY] Splitting User Input ---")
    try:
        user_query = state.get("user_query", "")
        if not user_query:
            return {"job_description": "", "generation_prompt": ""}

        if not language_model:
            raise RuntimeError("Inference engine is offline.")

        analysis_prompt = PromptTemplate.from_template(PROMPT_QUERY_ANALYSIS)
        response_parser = JsonOutputParser(pydantic_object=QueryAnalysisResult)
        analysis_chain = analysis_prompt | language_model | response_parser

        result = await analysis_chain.ainvoke({"user_query": user_query})
        
        # Robustly extract and ensure they are strings
        jd_val = result.get("job_description", "")
        gen_val = result.get("generation_prompt", "")
        
        jd = str(jd_val).strip() if not isinstance(jd_val, (dict, list)) else json.dumps(jd_val)
        gen = str(gen_val).strip() if not isinstance(gen_val, (dict, list)) else json.dumps(gen_val)
        
        # If the LLM failed to split but found a JD, provide a default generation prompt
        if jd and not gen:
            gen = "Generate 3 diverse and highly relevant candidate profiles for this role."
            
        return {
            "job_description": jd,
            "generation_prompt": gen
        }
    except Exception as e:
        print(f"Query Analysis Fault: {e}")
        # Baseline fallback: use entire query as JD
        return {"job_description": str(state.get("user_query", "")), "generation_prompt": "Generate 3 relevant profiles."}

# --- WORKFLOW NODE: CANDIDATE GENERATION ---
async def generate_candidates_node(state: WorkflowState) -> WorkflowState:
    """
    GENERATION NODE: Produces synthetic candidate profiles based on instructions.
    """
    print("--- [NODE: GENERATE CANDIDATES] Synthesizing Profiles ---")
    try:
        gen_prompt = state.get("generation_prompt", "")
        
        if not language_model:
            raise RuntimeError("Inference engine is offline.")

        generation_prompt_tmpl = PromptTemplate.from_template(PROMPT_CANDIDATE_GENERATION)
        response_parser = JsonOutputParser()
        generation_chain = generation_prompt_tmpl | language_model | response_parser

        raw_profiles = await generation_chain.ainvoke({
            "generation_prompt": gen_prompt
        })
        
        # Ensure it's a list of strings
        if isinstance(raw_profiles, dict) and "profiles" in raw_profiles:
            profile_list = raw_profiles["profiles"]
        else:
            profile_list = raw_profiles if isinstance(raw_profiles, list) else [str(raw_profiles)]

        return {"raw_candidate_profiles": profile_list}
    except Exception as e:
        print(f"Candidate Generation Fault: {e}")
        return {"raw_candidate_profiles": []}

# --- WORKFLOW NODE: CANDIDATE EVALUATION ---
async def evaluate_candidates_node(state: WorkflowState) -> WorkflowState:
    """
    CRITICAL NODE: Orchestrates the batch screening of candidate resumes.
    """
    print("--- [NODE: EVALUATE CANDIDATES] Starting Batch Technical Screening ---")
    try:
        job_description = state.get("job_description", "")
        raw_profiles = state.get("raw_candidate_profiles", [])
        
        if not raw_profiles or not job_description:
            print("Warning: Missing input data for evaluation.")
            return {"processed_evaluations": [], "qualified_matches": []}

        if not language_model:
            raise RuntimeError("Inference engine is offline.")

        formatted_profiles = "\n\n".join([f"--- Candidate {i+1} ---\n{p}" for i, p in enumerate(raw_profiles)])
        
        screening_prompt = PromptTemplate.from_template(PROMPT_BATCH_CANDIDATE_SCREENING)
        response_parser = JsonOutputParser()
        screening_chain = screening_prompt | language_model | response_parser
        
        raw_llm_results = await screening_chain.ainvoke({
            "job_description": job_description, 
            "formatted_profiles": formatted_profiles
        })
        
        if isinstance(raw_llm_results, dict) and "candidates" in raw_llm_results:
            results_list = raw_llm_results["candidates"]
        else:
            results_list = raw_llm_results if isinstance(raw_llm_results, list) else [raw_llm_results]

        processed_evaluations = []
        qualified_matches = []
        
        for idx, result in enumerate(results_list):
            evaluation: CandidateEvaluation = {
                "candidate_id": idx,
                "candidate_name": result.get("name", f"Candidate {idx+1}"),
                "screening_score": int(result.get("score", 0)) if str(result.get("score", 0)).isdigit() else 0,
                "is_technical_match": robust_bool(result.get("is_match", False)),
                "evaluation_reasoning": result.get("reasoning", "No evaluation details provided."),
                "original_profile_text": raw_profiles[idx] if idx < len(raw_profiles) else ""
            }
            processed_evaluations.append(evaluation)
            if evaluation["is_technical_match"]:
                qualified_matches.append(evaluation)
                
        print(f"Evaluation Complete: {len(processed_evaluations)} profiles screened, {len(qualified_matches)} matches found.")
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
    """
    print("--- [NODE: GENERATE OUTREACH] Drafting Personalized Proposals ---")
    try:
        job_description = state.get("job_description", "")
        qualified_matches = state.get("qualified_matches", [])
        
        if not qualified_matches:
            return {
                "target_contact_email": "",
                "generated_email_draft": "No qualified matches identified for outreach.",
                "email_delivery_status": "Skipped"
            }

        if not language_model:
            raise RuntimeError("Inference engine is offline.")
            
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
        
        try:
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
    """
    print("--- [NODE: DELIVER OUTREACH] Initiating Email Transmission ---")
    try:
        target_email = state.get("target_contact_email", "")
        email_body = state.get("generated_email_draft", "")
        is_approved = state.get("is_approved", False)

        if not is_approved:
            print("⚠️ Transmission blocked: Awaiting human approval.")
            # Keep the status as "Drafted" so we don't re-draft unnecessarily
            return {"email_delivery_status": "Drafted - Awaiting Human Approval"}

        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, target_email)
        cleaned_email = match.group(0) if match else ""

        if not cleaned_email or not email_body:
            print(f"❌ Transmission failed: Missing/Invalid email metadata. (Extracted: '{cleaned_email}')")
            return {"email_delivery_status": f"Failed: Invalid target email ('{target_email}')"}

        delivery_report = execute_smtp_transmission(
            recipient=cleaned_email, 
            subject="Qualified Technical Matches - DIGOT AI Recruitment Analysis", 
            body=email_body
        )

        print(f"✅ Email transmission complete: {delivery_report}")
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
    Modified for stricter deterministic routing in production.
    """
    print("--- [NODE: SUPERVISOR] Analyzing State & Routing Workflow ---")
    try:
        # 1. Gather State Context
        has_jd = bool(state.get("job_description"))
        has_candidates = len(state.get("raw_candidate_profiles", [])) > 0
        has_evaluations = len(state.get("processed_evaluations", [])) > 0
        # Check draft content instead of just status string
        has_outreach = bool(state.get("generated_email_draft"))
        match_count = len(state.get("qualified_matches", []))
        is_approved = state.get("is_approved", False)
        delivery_status = state.get("email_delivery_status", "")

        print(f"State Summary: JD={has_jd}, Candidates={has_candidates}, Evals={has_evaluations}, Draft={has_outreach}, Matches={match_count}, Approved={is_approved}")

        # 2. DETERMINISTIC ROUTING (Primary)
        if not has_jd:
            next_agent = "analyze_query"
        elif not has_candidates:
            next_agent = "generate_candidates"
        elif not has_evaluations:
            # Only evaluate if we have profiles
            next_agent = "evaluate_candidates" if has_candidates else "FINISH"
        elif has_evaluations and match_count == 0:
            # STOP early if no matches found after screening
            print("📍 Routing Info: Evaluations complete but 0 matches. Ending workflow.")
            next_agent = "FINISH"
        elif match_count > 0 and not has_outreach:
            next_agent = "generate_outreach"
        elif has_outreach and is_approved:
            next_agent = "send_outreach"
        elif has_outreach and not is_approved:
            # CRITICAL: If we have a draft but no approval, we MUST stop and wait.
            print("📍 Routing Info: Outreach drafted. Awaiting human approval. Ending current run.")
            next_agent = "FINISH"
        else:
            # 3. LLM ROUTING (Fallback/Nuance)
            try:
                supervisor_prompt = PromptTemplate.from_template(PROMPT_RECRUITMENT_SUPERVISOR)
                supervisor_chain = supervisor_prompt | language_model
                
                response = await supervisor_chain.ainvoke({
                    "has_jd": "Yes" if has_jd else "No",
                    "has_candidates": "Yes" if has_candidates else "No",
                    "has_evaluations": "Yes" if has_evaluations else "No",
                    "has_outreach": "Yes" if has_outreach else "No",
                    "match_count": match_count,
                    "is_approved": "Yes" if is_approved else "No"
                })
                next_agent = response.content.strip()
                print(f"🤖 Supervisor Decision (LLM): {next_agent}")
                
                valid_agents = ["analyze_query", "generate_candidates", "evaluate_candidates", "generate_outreach", "send_outreach", "FINISH"]
                if next_agent not in valid_agents:
                    next_agent = "FINISH"
                
                # Double-check LLM approval logic
                if next_agent == "send_outreach" and not is_approved:
                    print("⚠️ LLM suggested send_outreach without approval. Overriding to FINISH.")
                    next_agent = "FINISH"

            except Exception as llm_err:
                print(f"Supervisor LLM Fault: {llm_err}")
                next_agent = "FINISH"

        print(f"📍 Final Routing Decision: {next_agent}")
        return {"next_destination": next_agent}

    except Exception as e:
        print(f"Supervisor Critical Fault: {e}")
        return {"next_destination": "FINISH"}
