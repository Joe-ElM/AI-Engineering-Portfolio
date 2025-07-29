from typing import List, Dict, Optional, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from datetime import datetime


#=============================================================================
# USER INPUT MODELS
#=============================================================================

class UserInput(BaseModel):
    symptoms: str = Field(description="User's described symptoms")
    age: Optional[int] = Field(description="User's age")
    gender: Optional[str] = Field(description="User's gender")
    medical_history: Optional[List[str]] = Field(default=[], description="Previous conditions")
    current_medications: Optional[List[str]] = Field(default=[], description="Current medications")
    allergies: Optional[List[str]] = Field(default=[], description="Known allergies")

#=============================================================================
# PATIENT CONTEXT MODELS - FIXED
#=============================================================================

class PatientContext(BaseModel):
    """Maintains cumulative patient information across conversations"""
    user_id: str = Field(default="", description="Unique user identifier")
    age: Optional[int] = Field(default=None, description="Patient age")  # FIXED: Made optional with default
    gender: Optional[str] = Field(default=None, description="Patient gender")  # FIXED: Made optional with default
    symptoms_timeline: Dict[str, List[str]] = Field(default_factory=dict, description="Symptoms by date")
    conditions: List[str] = Field(default_factory=list, description="Diagnosed conditions")
    lab_values: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Lab results with dates")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    recommendations_given: Dict[str, List[str]] = Field(default_factory=dict, description="Recommendations by category")
    user_feedback: Dict[str, str] = Field(default_factory=dict, description="Feedback on recommendations")
    lifestyle_factors: Dict[str, Any] = Field(default_factory=dict, description="Diet, exercise, habits")
    unresolved_questions: List[str] = Field(default_factory=list, description="Questions to follow up on")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Dietary restrictions")  # ADDED: Missing field
    last_updated: datetime = Field(default_factory=datetime.now)

class ConversationSummary(BaseModel):
    """Summary of current conversation session"""
    session_id: str
    key_facts_extracted: List[str]
    new_symptoms: List[str]
    new_lab_values: Dict[str, float]
    recommendations_made: List[str]
    follow_up_needed: List[str]
    timestamp: datetime

#=============================================================================
# AGENT STATE MODELS
#=============================================================================

class TriageResult(BaseModel):
    intent_classification: str
    urgency_level: str  # LOW, MEDIUM, HIGH, EMERGENCY
    emergency_flags: List[str]
    routing_decision: str
    confidence_score: float

class DiagnosisResult(BaseModel):
    symptoms: List[str]
    symptom_analysis: Dict[str, Any]
    possible_conditions: List[Dict[str, Any]]
    severity_level: str
    recommended_tests: List[str]
    red_flags: List[str]
    research_sources: List[str]

class DietResult(BaseModel):
    diagnosed_condition: str
    dietary_restrictions: List[str]
    nutritional_needs: Dict[str, Any]
    recommended_foods: List[str]
    foods_to_avoid: List[str]
    meal_suggestions: List[str]
    supplements: List[str]

class TreatmentResult(BaseModel):
    diagnosis: Dict[str, Any]
    treatment_options: List[Dict[str, Any]]
    care_recommendations: List[str]
    lifestyle_changes: List[str]
    follow_up_schedule: Dict[str, Any]
    when_to_see_doctor: str
    appointment_needed: bool

class SynthesisResult(BaseModel):
    all_agent_outputs: Dict[str, Any]
    safety_validations: List[str]
    cross_checks: Dict[str, Any]
    final_recommendations: Dict[str, Any]
    appointment_needed: bool
    priority_level: str


class HallucinationCheck(BaseModel):
    source_citations: List[str]
    fact_verification: Dict[str, Any]
    consistency_score: float
    medical_accuracy: Dict[str, Any]
    flagged_claims: List[str]
    validation_status: str  # APPROVED, FLAGGED, REJECTED

#=============================================================================
# MAIN AGENT STATE - UPDATED
#=============================================================================

class MultiAgentHealthState(TypedDict):
    user_input: UserInput
    user_id: Optional[str]
    conversation_id: str
    
    # Patient Context - NEW
    patient_context: Optional[PatientContext]
    conversation_summary: Optional[ConversationSummary]
    
    # Agent Results
    triage_result: Optional[TriageResult]
    diagnosis_result: Optional[DiagnosisResult]
    diet_result: Optional[DietResult]
    treatment_result: Optional[TreatmentResult]
    synthesis_result: Optional[SynthesisResult]
    hallucination_check: Optional[HallucinationCheck]
    
    # Shared Context
    research_content: str
    conversation_history: List[str]
    personality: str
    openai_settings: Dict[str, float]
    
    # Final Output
    response: str
    execution_metadata: Dict[str, Any]

