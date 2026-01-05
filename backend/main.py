"""
FastAPI Backend - DIGOT AI Recruitment Orchestrator

Provides REST API endpoints for the recruitment pipeline:
- POST /api/v1/recruitment/execute: Initiates workflow and returns draft
- POST /api/v1/recruitment/approve: Resumes workflow with HITL approval
- GET /health: Service health check

The backend acts as a bridge between the Streamlit frontend and the LangGraph agent.
"""

import os
import sys
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- PATH CONFIGURATION ---
# Appending project root to sys.path to resolve internal 'agent' module.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Internal Module Imports
from agent.graph import initialize_recruitment_workflow

# Load global configuration
load_dotenv()

# --- FASTAPI CONFIGURATION ---
app = FastAPI(
    title="DIGOT AI - Recruitment Pipeline API",
    description="High-performance multi-agent system for candidate screening and outreach.",
    version="1.0.0"
)

# --- CORS MIDDLEWARE ---
# Enables secure cross-origin requests (essential for production APIs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- DATA TRANSFER OBJECTS (DTOs) ---

class PipelineRequestDTO(BaseModel):
    """Schema for incoming recruitment requests."""
    user_query: str

class CandidateEvaluationDTO(BaseModel):
    """Schema for reporting individual candidate evaluation results."""
    candidate_name: str
    screening_score: int
    is_technical_match: bool
    evaluation_reasoning: str

class WorkflowResponseDTO(BaseModel):
    """Consolidated schema for the final workflow response."""
    total_processed: int
    matched_count: int
    qualified_matches: List[CandidateEvaluationDTO]
    outreach_email_status: str
    outreach_email_draft: str
    target_contact_email: str
    # Full state to be passed back for approval if needed
    full_state: dict 

class ApprovalRequestDTO(BaseModel):
    """Schema for approving a drafted outreach email."""
    state: dict

# --- WORKFLOW ENGINE INITIALIZATION ---
# Pre-compile the recruitment workflow graph
recruitment_workflow = initialize_recruitment_workflow()

# --- API ENDPOINTS ---

@app.get("/")
async def health_check():
    """Service health monitoring."""
    return {"status": "healthy", "service": "DIGOT AI Recruitment API"}

@app.post("/api/v1/recruitment/execute", response_model=WorkflowResponseDTO)
async def execute_recruitment_flow(request: PipelineRequestDTO):
    """
    Primary endpoint to trigger the AI-driven recruitment orchestrator.
    """
    if not request.user_query:
        raise HTTPException(
            status_code=400, 
            detail="Incomplete request: User query is required."
        )

    # Transform request to initial WorkflowState
    workflow_input = {
        "user_query": request.user_query,
        "job_description": "",
        "generation_prompt": "",
        "raw_candidate_profiles": [],
        "processed_evaluations": [],
        "qualified_matches": [],
        "target_contact_email": "",
        "generated_email_draft": "",
        "email_delivery_status": "",
        "next_destination": "",
        "is_approved": False
    }

    try:
        # Await the execution of the LangGraph workflow
        execution_result = await recruitment_workflow.ainvoke(workflow_input)
        
        # Transform WorkflowState back to Response DTO
        qualified_matches_data = [
            CandidateEvaluationDTO(
                candidate_name=match.get("candidate_name", "Unknown"),
                screening_score=match.get("screening_score", 0),
                is_technical_match=match.get("is_technical_match", False),
                evaluation_reasoning=match.get("evaluation_reasoning", "")
            )
            for match in execution_result.get("qualified_matches", [])
        ]
        
        return WorkflowResponseDTO(
            total_processed=len(execution_result.get("raw_candidate_profiles", [])),
            matched_count=len(qualified_matches_data),
            qualified_matches=qualified_matches_data,
            outreach_email_status=execution_result.get("email_delivery_status", "Unknown"),
            outreach_email_draft=execution_result.get("generated_email_draft", ""),
            target_contact_email=execution_result.get("target_contact_email", ""),
            full_state=execution_result
        )

    except Exception as e:
        # Graceful handling of workflow-level failures
        print(f"Workflow Execution Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Workflow Execution Failure: {str(e)}"
        )

@app.post("/api/v1/recruitment/approve", response_model=WorkflowResponseDTO)
async def approve_outreach_flow(request: ApprovalRequestDTO):
    """
    Second phase of HITL: Approves the draft and triggers email delivery.
    """
    try:
        # Update state to approved
        state = request.state
        state["is_approved"] = True
        
        # Resume workflow
        execution_result = await recruitment_workflow.ainvoke(state)
        
        qualified_matches_data = [
            CandidateEvaluationDTO(
                candidate_name=match.get("candidate_name", "Unknown"),
                screening_score=match.get("screening_score", 0),
                is_technical_match=match.get("is_technical_match", False),
                evaluation_reasoning=match.get("evaluation_reasoning", "")
            )
            for match in execution_result.get("qualified_matches", [])
        ]
        
        return WorkflowResponseDTO(
            total_processed=len(state.get("raw_candidate_profiles", [])),
            matched_count=len(qualified_matches_data),
            qualified_matches=qualified_matches_data,
            outreach_email_status=execution_result.get("email_delivery_status", "Unknown"),
            outreach_email_draft=execution_result.get("generated_email_draft", ""),
            target_contact_email=execution_result.get("target_contact_email", ""),
            full_state=execution_result
        )
    except Exception as e:
        print(f"Approval Workflow Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Approval Failure: {str(e)}")

# --- SERVER STARTUP ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
