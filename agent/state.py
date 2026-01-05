"""
Workflow State Definitions - DIGOT AI Recruitment Orchestrator

Defines TypedDict schemas for state management across the LangGraph workflow.
All nodes read from and write to these standardized state structures.
"""

from typing import List, TypedDict, Optional

class CandidateEvaluation(TypedDict):
    """Represents the structured evaluation results for a single candidate profile."""
    candidate_id: int
    candidate_name: str
    screening_score: int
    is_technical_match: bool
    evaluation_reasoning: str
    original_profile_text: str

class WorkflowState(TypedDict):
    """Maintains the global state of the recruitment pipeline across all nodes."""
    user_query: str
    job_description: str
    generation_prompt: str
    raw_candidate_profiles: List[str]
    processed_evaluations: List[CandidateEvaluation]
    qualified_matches: List[CandidateEvaluation]
    target_contact_email: str
    generated_email_draft: str
    email_delivery_status: str
    next_destination: str
    is_approved: bool
