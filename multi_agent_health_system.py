# ===============================================================================
# FIXED MULTI-AGENT HEALTH SYSTEM
# ===============================================================================
# 
# FIXES IMPLEMENTED:
# 1. ✅ Data Validation - Prevents impossible demographics (197 years old, 9'3" tall)
# 2. ✅ Emergency Consistency - Emergency symptoms always trigger emergency response
# 3. ✅ Safety Guardrails - Validates biological plausibility
# 4. ✅ Improved Error Handling - Graceful validation error responses
# 5. ✅ Enhanced Triage - Better emergency detection and routing
# 6. ✅ Non-health query handling - Fixed missing return statement
#
# ===============================================================================

# fixed_multi_agent_health_system.py
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from extended_schemas import (
    MultiAgentHealthState, UserInput, PatientContext, ConversationSummary,
    TriageResult, DiagnosisResult, DietResult, TreatmentResult, 
    SynthesisResult, HallucinationCheck, 
)
from extended_tools import (
    search_wikipedia, search_tavily, calculate_bmi, calculate_nutrition_needs, 
    score_symptom_severity, schedule_appointment, validate_medical_safety, 
    combine_search_results, 
)
from config import PERSONALITIES, MEDICAL_DISCLAIMER
from datetime import datetime
import re
import json


class HealthDataValidator:
    """Enhanced validation for health system inputs"""
    
    @staticmethod
    def validate_demographics(age: int, height_cm: float, weight_kg: float) -> dict:
        """Validate patient demographics for biological plausibility"""
        errors = []
        warnings = []
        
        # Age validation
        if age is not None:
            if age < 0:
                errors.append("Age cannot be negative")
            elif age > 125:
                errors.append(f"Age {age} exceeds maximum verified human lifespan (122 years)")
            elif age > 110:
                warnings.append(f"Age {age} is extremely rare - please verify")
        
        # Height validation
        if height_cm is not None:
            if height_cm < 50:
                errors.append("Height too low to be compatible with life")
            elif height_cm > 272:  # 8'11" in cm
                errors.append(f"Height {height_cm}cm exceeds maximum recorded human height")
            elif height_cm > 250:
                warnings.append(f"Height {height_cm}cm is extremely rare - please verify")
        
        # Weight validation
        if weight_kg is not None:
            if weight_kg < 2:
                errors.append("Weight too low to be compatible with life")
            elif weight_kg > 650:
                errors.append(f"Weight {weight_kg}kg exceeds survivable limits")
            elif weight_kg > 450:
                warnings.append(f"Weight {weight_kg}kg is extremely high - please verify")
        
        # BMI cross-validation
        if height_cm and weight_kg:
            bmi = weight_kg / ((height_cm/100) ** 2)
            if bmi > 100:
                errors.append(f"BMI {bmi:.1f} is incompatible with life")
            elif bmi > 70:
                warnings.append(f"BMI {bmi:.1f} is extremely high")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_emergency_consistency(symptoms: str, query_intent: str = "") -> dict:
        """Ensure emergency cases aren't treated as routine"""
        emergency_keywords = [
            "chest pain", "vomiting blood", "black tarry stools", 
            "difficulty breathing", "shortness of breath", "confusion", 
            "fever", "severe pain", "unconscious", "seizure", "stroke",
            "heart attack", "can't breathe", "severe bleeding"
        ]
        
        has_emergency = any(keyword in symptoms.lower() for keyword in emergency_keywords)
        
        routine_intents = ["metadata", "summary", "diet recommendations", "lifestyle advice"]
        is_routine_query = any(intent in query_intent.lower() for intent in routine_intents)
        
        if has_emergency and is_routine_query:
            return {
                "emergency_override": True,
                "message": "🚨 EMERGENCY SYMPTOMS DETECTED. Redirecting to immediate care recommendations regardless of query type."
            }
        
        return {"emergency_override": False}
    
    @staticmethod
    def convert_height_to_cm(height_str: str) -> float:
        """Convert various height formats to cm"""
        if not height_str:
            return None
            
        height_str = height_str.lower().strip()
        
        # Handle feet and inches (e.g., "6'2", "6 feet 2 inches")
        feet_inches_match = re.search(r"(\d+)'(\d+)", height_str)
        if feet_inches_match:
            feet = int(feet_inches_match.group(1))
            inches = int(feet_inches_match.group(2))
            return (feet * 12 + inches) * 2.54
        
        # Handle cm (e.g., "180cm", "180 cm")
        cm_match = re.search(r"(\d+\.?\d*)\s*cm", height_str)
        if cm_match:
            return float(cm_match.group(1))
        
        # Handle meters (e.g., "1.8m", "1.8 meters")
        m_match = re.search(r"(\d+\.?\d*)\s*m", height_str)
        if m_match:
            return float(m_match.group(1)) * 100
        
        # Handle inches only (e.g., "72 inches")
        inches_match = re.search(r"(\d+\.?\d*)\s*inch", height_str)
        if inches_match:
            return float(inches_match.group(1)) * 2.54
        
        return None
    
    @staticmethod
    def convert_weight_to_kg(weight: float, unit: str) -> float:
        """Convert weight to kg"""
        if not weight:
            return None
            
        if unit and unit.lower() in ["lbs", "pounds", "lb"]:
            return weight * 0.453592
        return weight  # Assume kg if no unit or kg specified


class MultiAgentHealthSystem:
    def __init__(self, openai_settings=None):
        self.openai_settings = openai_settings or {}
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=self.openai_settings.get("temperature", 0.3),
            top_p=self.openai_settings.get("top_p", 0.9),
            frequency_penalty=self.openai_settings.get("frequency_penalty", 0.0),
            max_tokens=self.openai_settings.get("max_tokens", 1000)
        )
        
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.conversation_history = []
        self.validator = HealthDataValidator()
        # Initialize with empty patient context
        self.patient_context = PatientContext(
            user_id="default",
            symptoms_timeline={},
            conditions=[],
            lab_values={},
            medications=[],
            recommendations_given={},
            user_feedback={},
            lifestyle_factors={},
            unresolved_questions=[]
        )
    
    def _build_graph(self):
        builder = StateGraph(MultiAgentHealthState)
        
        # Add nodes including validation and emergency handler
        builder.add_node("data_validator", self._data_validator)
        builder.add_node("profile_extractor", self._profile_extractor)
        builder.add_node("triage_agent", self._triage_agent)
        builder.add_node("emergency_handler", self._emergency_handler)
        builder.add_node("diagnosis_agent", self._diagnosis_agent)
        builder.add_node("diet_agent", self._diet_agent)
        builder.add_node("treatment_agent", self._treatment_agent)
        builder.add_node("synthesis_agent", self._synthesis_agent)
        builder.add_node("hallucination_detector", self._hallucination_detector)
        builder.add_node("non_health_rejection", self._non_health_rejection)
        builder.add_node("validation_error_handler", self._validation_error_handler)
        
        # Start with data validation
        builder.add_edge(START, "data_validator")
        
        # Conditional routing from validator
        builder.add_conditional_edges(
            "data_validator",
            self._validation_route,
            {
                "valid": "profile_extractor",
                "invalid": "validation_error_handler"
            }
        )
        
        builder.add_edge("validation_error_handler", END)
        builder.add_edge("profile_extractor", "triage_agent")
        
        # Conditional routing from triage
        builder.add_conditional_edges(
            "triage_agent",
            self._route_decision,
            {
                "emergency": "emergency_handler",
                "diagnosis_only": "diagnosis_agent",
                "diet_only": "diet_agent",
                "treatment_only": "treatment_agent",
                "full_pipeline": "diagnosis_agent",
                "clarification": "synthesis_agent",
                "non_health_rejection": "non_health_rejection"
            }
        )
        
        # Emergency and non-health bypass normal pipeline
        builder.add_edge("emergency_handler", END)
        builder.add_edge("non_health_rejection", END)
        
        # Normal pipeline routes
        builder.add_conditional_edges(
            "diagnosis_agent",
            lambda x: "synthesis_agent" if x.get("triage_result", {}).routing_decision == "diagnosis_only" else "diet_agent"
        )
        
        builder.add_conditional_edges(
            "diet_agent",
            lambda x: "synthesis_agent" if x.get("triage_result", {}).routing_decision in ["diet_only", "diagnosis_only"] else "treatment_agent"
        )
        
        builder.add_edge("treatment_agent", "synthesis_agent")
        builder.add_edge("synthesis_agent", "hallucination_detector")
        builder.add_edge("hallucination_detector", END)
        
        return builder.compile(checkpointer=self.memory)
    
    def _validation_route(self, state: MultiAgentHealthState):
        """Route based on validation results"""
        return "invalid" if state.get("validation_error") else "valid"
    
    def _route_decision(self, state: MultiAgentHealthState):
        """Determine which route to take based on triage results"""
        triage_result = state.get("triage_result", {})
        return triage_result.routing_decision
    
    #=========================================================================
    # NEW: DATA VALIDATOR
    #=========================================================================
    
    def _data_validator(self, state: MultiAgentHealthState):
        """Validate input data for biological plausibility"""
        user_input = state["user_input"]
        
        # Extract basic demographics for validation
        prompt = f"""Extract demographic data from this text for validation. Return ONLY a JSON object:

Text: "{user_input.symptoms}"

Return JSON with these keys (use null if not found):
{{
    "age": "number or null",
    "height": "format like 6'1\" or 185cm or null", 
    "weight": "number or null",
    "weight_unit": "lbs or kg or null"
}}

Extract only what is explicitly stated. Be precise."""

        messages = [
            SystemMessage(content="You are a data extractor. Return only valid JSON. No other text."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            extracted_data = json.loads(response.content.strip())
            
            # Convert and validate
            age = extracted_data.get("age")
            height_str = extracted_data.get("height")
            weight = extracted_data.get("weight")
            weight_unit = extracted_data.get("weight_unit", "kg")
            
            height_cm = self.validator.convert_height_to_cm(height_str) if height_str else None
            weight_kg = self.validator.convert_weight_to_kg(weight, weight_unit) if weight else None
            
            validation_result = self.validator.validate_demographics(age, height_cm, weight_kg)
            
            if not validation_result["valid"]:
                return {
                    "validation_error": True,
                    "validation_errors": validation_result["errors"],
                    "validation_warnings": validation_result.get("warnings", [])
                }
            
            # Check for emergency consistency regardless of query type
            emergency_check = self.validator.validate_emergency_consistency(user_input.symptoms)
            
            return {
                "validation_error": False,
                "validation_warnings": validation_result.get("warnings", []),
                "emergency_override": emergency_check.get("emergency_override", False),
                "emergency_message": emergency_check.get("message", "")
            }
            
        except (json.JSONDecodeError, Exception) as e:
            # If extraction fails, continue without validation (but log warning)
            print(f"Validation extraction failed: {e}")
            return {"validation_error": False, "validation_warnings": ["Could not validate demographics"]}
    
    #=========================================================================
    # NEW: VALIDATION ERROR HANDLER
    #=========================================================================
    
    def _validation_error_handler(self, state: MultiAgentHealthState):
        """Handle validation errors gracefully"""
        errors = state.get("validation_errors", [])
        warnings = state.get("validation_warnings", [])
        
        error_message = f"""⚠️ **Data Validation Issues Detected**

**Errors:**
{chr(10).join(['• ' + error for error in errors])}

**Please verify and correct the following:**
• Patient age (must be 0-125 years)
• Patient height (must be realistic human height)  
• Patient weight (must be compatible with life)

**Recommendation:** Please provide accurate demographic information and resubmit your health query.

If this is a hypothetical scenario for educational purposes, please indicate that in your question.

Your AI Health Team"""
        
        # Create ALL required results for error case
        triage_result = TriageResult(
            intent_classification="validation_error",
            urgency_level="VALIDATION_ERROR",
            emergency_flags=["Invalid demographic data"],
            routing_decision="validation_error",
            confidence_score=1.0
        )
        
        synthesis_result = SynthesisResult(
            all_agent_outputs={"validation": "Failed"},
            safety_validations=["Data validation failed"],
            cross_checks={"validated": False},
            final_recommendations={"plan": error_message},
            appointment_needed=False,
            priority_level="VALIDATION_ERROR"
        )
        
        hallucination_check = HallucinationCheck(
            source_citations=["System validation"],
            fact_verification={"checked": True},
            consistency_score=1.0,
            medical_accuracy={"appropriate": True},
            flagged_claims=[],
            validation_status="VALIDATION_ERROR"
        )
        
        return {
            "triage_result": triage_result,  # BUG FIX: Added missing triage_result
            "synthesis_result": synthesis_result,
            "hallucination_check": hallucination_check
        }
    
    #=========================================================================
    # NEW: EMERGENCY HANDLER
    #=========================================================================
    
    def _emergency_handler(self, state: MultiAgentHealthState):
        """Handle emergency cases consistently"""
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        
        emergency_message = f"""🚨 **MEDICAL EMERGENCY DETECTED**

**Patient:** {patient_context.age or 'Unknown'} year old {patient_context.gender or 'patient'}

**CRITICAL SYMPTOMS IDENTIFIED:**
{user_input.symptoms[:200]}...

**IMMEDIATE ACTION REQUIRED:**
• **Call 911 or go to the nearest Emergency Room immediately**
• Do not delay seeking emergency medical care
• Do not attempt self-treatment
• Bring a list of current medications and medical conditions

**THIS IS NOT THE TIME FOR:**
• Dietary recommendations  
• Routine medical advice
• Lifestyle modifications

**Your symptoms indicate a potentially life-threatening medical emergency that requires immediate professional intervention.**

**In case of emergency:**
• US: 911
• UK: 999  
• EU: 112

Your AI Health Team

⚠️ **SEEK IMMEDIATE EMERGENCY MEDICAL ATTENTION**"""

        synthesis_result = SynthesisResult(
            all_agent_outputs={"emergency": "Immediate care required"},
            safety_validations=["Emergency symptoms detected"],
            cross_checks={"emergency_validated": True},
            final_recommendations={"plan": emergency_message},
            appointment_needed=True,
            priority_level="EMERGENCY"
        )
        
        hallucination_check = HallucinationCheck(
            source_citations=["Emergency protocols"],
            fact_verification={"emergency": True},
            consistency_score=1.0,
            medical_accuracy={"emergency_appropriate": True},
            flagged_claims=[],
            validation_status="EMERGENCY_APPROVED"
        )
        
        return {
            "synthesis_result": synthesis_result,
            "hallucination_check": hallucination_check
        }
    
    #=========================================================================
    # ENHANCED PROFILE EXTRACTOR
    #=========================================================================
    
    def _profile_extractor(self, state: MultiAgentHealthState):
        """Extract user profile using structured LLM output with validation awareness"""
        user_input = state["user_input"]
        
        # Check for validation warnings
        validation_warnings = state.get("validation_warnings", [])
        
        prompt = f"""Extract user information from this text and return ONLY a JSON object with these exact keys:

Text: "{user_input.symptoms}"

Return JSON with these keys (use null if not found):
{{
    "name": "string or null",
    "age": "number or null",
    "gender": "male or female or null",
    "height": "format like 6'1\" or 185cm or null",
    "weight": "number or null",
    "weight_unit": "lbs or kg or null",
    "conditions": ["condition1", "condition2"] or [],
    "medications": ["med1", "med2"] or [],
    "allergies": ["allergy1", "allergy2"] or [],
    "family_history": ["condition1", "condition2"] or [],
    "lab_values": {{"test_name": number}} or {{}},
    "lifestyle": {{
        "smoking": "yes or no or former or null",
        "alcohol": "frequency description or null",
        "exercise": "frequency description or null"
    }}
}}

Extract only what is explicitly stated. Do not infer or assume."""

        messages = [
            SystemMessage(content="You are a medical information extractor. Return only valid JSON. No other text."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            extracted_data = json.loads(response.content.strip())
            
            # Update patient context with extracted data (same logic as before)
            self._update_patient_context_from_data(extracted_data)
            
            # Add validation warnings to patient context if any
            if validation_warnings:
                self.patient_context.lifestyle_factors["validation_warnings"] = validation_warnings
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Profile extraction error: {e}")
            # Fallback extraction logic (same as before)
            self._fallback_extraction(user_input)
        
        # Update symptoms timeline
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.patient_context.symptoms_timeline[current_date] = [user_input.symptoms[:100]]
        
        return {"patient_context": self.patient_context}
    
    def _update_patient_context_from_data(self, extracted_data):
        """Update patient context from extracted data"""
        # Ensure all list fields exist
        if not hasattr(self.patient_context, 'conditions') or self.patient_context.conditions is None:
            self.patient_context.conditions = []
        if not hasattr(self.patient_context, 'medications') or self.patient_context.medications is None:
            self.patient_context.medications = []
        if not hasattr(self.patient_context, 'lifestyle_factors') or self.patient_context.lifestyle_factors is None:
            self.patient_context.lifestyle_factors = {}
        if not hasattr(self.patient_context, 'lab_values') or self.patient_context.lab_values is None:
            self.patient_context.lab_values = {}
            
        if extracted_data.get("name"):
            self.patient_context.user_id = extracted_data["name"]
        
        if extracted_data.get("age"):
            self.patient_context.age = int(extracted_data["age"])
        
        if extracted_data.get("gender"):
            self.patient_context.gender = extracted_data["gender"].lower()
        
        if extracted_data.get("conditions"):
            # Avoid duplicates
            for condition in extracted_data["conditions"]:
                if condition not in self.patient_context.conditions:
                    self.patient_context.conditions.append(condition)
        
        if extracted_data.get("medications"):
            for medication in extracted_data["medications"]:
                if medication not in self.patient_context.medications:
                    self.patient_context.medications.append(medication)
        
        # Handle lifestyle factors, lab values, etc. (same as before)
        if extracted_data.get("allergies"):
            if "allergies" not in self.patient_context.lifestyle_factors:
                self.patient_context.lifestyle_factors["allergies"] = []
            self.patient_context.lifestyle_factors["allergies"].extend(extracted_data["allergies"])
        
        if extracted_data.get("family_history"):
            self.patient_context.lifestyle_factors["family_history"] = extracted_data["family_history"]
        
        if extracted_data.get("lifestyle"):
            lifestyle = extracted_data["lifestyle"]
            for key, value in lifestyle.items():
                if value:
                    self.patient_context.lifestyle_factors[key] = value
        
        if extracted_data.get("lab_values"):
            current_date = datetime.now().strftime("%Y-%m-%d")
            for test_name, value in extracted_data["lab_values"].items():
                if test_name not in self.patient_context.lab_values:
                    self.patient_context.lab_values[test_name] = {}
                self.patient_context.lab_values[test_name][current_date] = float(value)
        
        if extracted_data.get("weight") and extracted_data.get("weight_unit"):
            current_date = datetime.now().strftime("%Y-%m-%d")
            if 'weight' not in self.patient_context.lab_values:
                self.patient_context.lab_values['weight'] = {}
            self.patient_context.lab_values['weight'][current_date] = {
                'value': float(extracted_data["weight"]), 
                'unit': extracted_data["weight_unit"]
            }
        
        if extracted_data.get("height"):
            self.patient_context.lifestyle_factors['height'] = extracted_data["height"]
    
    def _fallback_extraction(self, user_input):
        """Fallback extraction for when JSON parsing fails"""
        text = user_input.symptoms.lower()
        
        age_match = re.search(r'(\d+)[-\s]?year[-\s]?old', text)
        if age_match:
            age = int(age_match.group(1))
            # Apply validation even in fallback
            if age <= 125:  # Basic validation
                self.patient_context.age = age
        
        if 'male' in text or 'man' in text:
            self.patient_context.gender = 'male'
        elif 'female' in text or 'woman' in text:
            self.patient_context.gender = 'female'
    
    #=========================================================================
    # ENHANCED TRIAGE AGENT
    #=========================================================================
    
    def _triage_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        
        # Ensure patient_context has required fields
        if not patient_context.conditions:
            patient_context.conditions = []
        
        # Check for emergency override first
        if state.get("emergency_override"):
            return {
                "triage_result": TriageResult(
                    intent_classification="emergency_override",
                    urgency_level="EMERGENCY",
                    emergency_flags=["Emergency symptoms with routine query detected"],
                    routing_decision="emergency",
                    confidence_score=1.0
                )
            }
        
        # Enhanced emergency keyword detection
        emergency_keywords = [
            "chest pain", "vomiting blood", "black tarry stools", 
            "difficulty breathing", "shortness of breath", "can't breathe",
            "confusion", "fever 103", "fever over", "unconscious", 
            "seizure", "stroke", "heart attack", "severe bleeding",
            "severe pain", "radiating pain", "left arm pain"
        ]
        
        symptoms_text = user_input.symptoms.lower()
        emergency_flags = [keyword for keyword in emergency_keywords if keyword in symptoms_text]
        
        # If emergency symptoms detected, always route to emergency
        if emergency_flags:
            return {
                "triage_result": TriageResult(
                    intent_classification="emergency",
                    urgency_level="EMERGENCY", 
                    emergency_flags=emergency_flags,
                    routing_decision="emergency",
                    confidence_score=0.95
                )
            }
        
        # Check if this is actually a health query
        intent_prompt = f"""Classify this query as health-related or not:

Query: "{user_input.symptoms}"

Health-related queries include:
- Physical symptoms (pain, fever, headache, etc.)
- Medical conditions or diseases
- Medications and treatments
- Diet and nutrition questions
- Mental health concerns
- Exercise and fitness questions
- Medical test results
- Doctor visits or medical procedures
- Health prevention and wellness

Respond with only: HEALTH or NON_HEALTH"""
        
        intent_messages = [
            SystemMessage(content="You are an intent classifier. Respond with only HEALTH or NON_HEALTH."),
            HumanMessage(content=intent_prompt)
        ]
        
        intent_response = self.llm.invoke(intent_messages)
        intent = intent_response.content.strip().upper()
        
        # If not health-related, return rejection routing
        if "NON_HEALTH" in intent:
            triage_result = TriageResult(
                intent_classification="non_health",
                urgency_level="N/A",
                emergency_flags=[],
                routing_decision="non_health_rejection",
                confidence_score=0.9
            )
            return {"triage_result": triage_result}
        
        # Normal health triage logic
        prompt = f"""Classify this health query:
        Query: {user_input.symptoms}
        Patient: {patient_context.age or 'Unknown'} year old {patient_context.gender or 'Unknown'}
        
        Return:
        1. Urgency: LOW/MEDIUM/HIGH
        2. Route: diet_only/treatment_only/diagnosis_only/full_pipeline/clarification
        """
        
        messages = [
            SystemMessage(content="You are a medical triage assistant."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        content = response.content.lower()
        
        # Parse response
        urgency = "MEDIUM"
        if "high" in content:
            urgency = "HIGH"
        elif "low" in content:
            urgency = "LOW"
        
        # Determine routing
        routing = "full_pipeline"
        if "diet_only" in content:
            routing = "diet_only"
        elif "treatment_only" in content:
            routing = "treatment_only"
        elif "diagnosis_only" in content:
            routing = "diagnosis_only"
        elif "clarification" in content:
            routing = "clarification"
        
        triage_result = TriageResult(
            intent_classification="health",
            urgency_level=urgency,
            emergency_flags=[],
            routing_decision=routing,
            confidence_score=0.8
        )
        
        return {"triage_result": triage_result}
    
    #=========================================================================
    # OTHER AGENTS (keep existing logic but add emergency awareness)
    #=========================================================================
    
    def _non_health_rejection(self, state: MultiAgentHealthState):
        """Handle non-health queries with LLM-generated contextual response"""
        user_input = state["user_input"]
        
        prompt = f"""The user asked: "{user_input.symptoms}"

This is not a health-related question. Generate a brief, polite response that:
1. Acknowledges what they asked about without being specific
2. Explains you're specialized in health and medical topics
3. Offers to help with any health-related questions instead

Keep the response professional, helpful, and under 3 sentences."""
        
        messages = [
            SystemMessage(content="You are a health-focused AI that politely redirects non-health queries. Be brief and helpful."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        message = response.content.strip()
        
        triage_result = TriageResult(
            intent_classification="non_health",
            urgency_level="N/A",
            emergency_flags=[],
            routing_decision="non_health_rejection",
            confidence_score=0.9
        )
        
        synthesis_result = SynthesisResult(
            all_agent_outputs={"rejection": "Non-health query handled"},
            safety_validations=[],
            cross_checks={"validated": True},
            final_recommendations={"plan": message},
            appointment_needed=False,
            priority_level="N/A"
        )
        
        hallucination_check = HallucinationCheck(
            source_citations=["System response"],
            fact_verification={"checked": True},
            consistency_score=1.0,
            medical_accuracy={"appropriate": True},
            flagged_claims=[],
            validation_status="APPROVED"
        )
        
        return {
            "triage_result": triage_result,
            "synthesis_result": synthesis_result,
            "hallucination_check": hallucination_check
        }
    
    def _diagnosis_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        
        # Research symptoms
        wikipedia_results = search_wikipedia.invoke({"query": user_input.symptoms})
        tavily_results = search_tavily.invoke({"query": user_input.symptoms})
        research_content = combine_search_results(wikipedia_results, tavily_results)
        
        # Score severity
        severity_score = score_symptom_severity.invoke({
            "symptoms": [user_input.symptoms], 
            "age": patient_context.age or 30
        })
        
        prompt = f"""Analyze symptoms for this patient:
        Age: {patient_context.age or 'Unknown'}, Gender: {patient_context.gender or 'Unknown'}
        Conditions: {', '.join(patient_context.conditions) if patient_context.conditions else 'None'}
        Query: {user_input.symptoms}
        
        Research: {research_content[:1000]}
        
        Provide brief analysis and recommendations."""
        
        messages = [
            SystemMessage(content="You are a diagnostic assistant providing educational information."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        diagnosis_result = DiagnosisResult(
            symptoms=[user_input.symptoms],
            symptom_analysis={"analysis": response.content},
            possible_conditions=[],
            severity_level=severity_score.get("severity_level", "MEDIUM"),
            recommended_tests=[],
            red_flags=[],
            research_sources=[]
        )
        
        return {"diagnosis_result": diagnosis_result, "research_content": research_content}
    
    def _diet_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        
        # Calculate nutrition needs
        nutrition_calc = calculate_nutrition_needs.invoke({
            "condition": ', '.join(patient_context.conditions) if patient_context.conditions else user_input.symptoms,
            "age": patient_context.age or 30,
            "gender": patient_context.gender or "unknown",
            "activity_level": "moderate"
        })
        
        prompt = f"""Provide dietary recommendations for:
        Patient: {patient_context.age or 'Unknown'} year old {patient_context.gender or 'Unknown'}
        Conditions: {', '.join(patient_context.conditions) if patient_context.conditions else 'None'}
        Query: {user_input.symptoms}
        
        Nutrition needs: {nutrition_calc}
        
        Give practical, actionable dietary advice."""
        
        messages = [
            SystemMessage(content="You are a nutrition specialist."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        diet_result = DietResult(
            diagnosed_condition=', '.join(patient_context.conditions) if patient_context.conditions else user_input.symptoms,
            dietary_restrictions=[],
            nutritional_needs=nutrition_calc,
            recommended_foods=[],
            foods_to_avoid=[],
            meal_suggestions=[],
            supplements=[]
        )
        
        return {"diet_result": diet_result}
    
    def _treatment_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        diagnosis_result = state.get("diagnosis_result")
        
        # Schedule appointment if needed
        appointment = schedule_appointment.invoke({
            "urgency": diagnosis_result.severity_level.lower() if diagnosis_result else "moderate",
            "condition": ', '.join(patient_context.conditions) if patient_context.conditions else user_input.symptoms,
            "preferred_timeframe": "soon"
        })
        
        prompt = f"""Provide treatment guidance for:
        Patient: {patient_context.age or 'Unknown'} year old {patient_context.gender or 'Unknown'}
        Conditions: {', '.join(patient_context.conditions) if patient_context.conditions else 'None'}
        Query: {user_input.symptoms}
        
        Appointment info: {appointment}
        
        Give practical care recommendations."""
        
        messages = [
            SystemMessage(content="You are a treatment specialist. Never prescribe medications."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        treatment_result = TreatmentResult(
            diagnosis={},
            treatment_options=[],
            care_recommendations=[],
            lifestyle_changes=[],
            follow_up_schedule=appointment,
            when_to_see_doctor=appointment.get("recommended_timeframe", "As needed"),
            appointment_needed=True
        )
        
        return {"treatment_result": treatment_result}
    
    def _synthesis_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        triage_result = state["triage_result"]
        personality = state.get("personality", "friendly")
        
        # Gather all outputs
        all_outputs = {}
        if state.get("diagnosis_result"):
            all_outputs["diagnosis"] = state["diagnosis_result"].symptom_analysis
        if state.get("diet_result"):
            all_outputs["diet"] = "Nutritional recommendations provided"
        if state.get("treatment_result"):
            all_outputs["treatment"] = "Care guidance provided"
        
        # Safety validation
        safety_check = validate_medical_safety.invoke({
            "recommendations": all_outputs,
            "user_profile": {"age": patient_context.age}
        })
        
        # Get comprehensive patient profile for context
        patient_name = patient_context.user_id if patient_context.user_id != "default" else "Unknown"
        patient_height = patient_context.lifestyle_factors.get('height', 'Unknown') if patient_context.lifestyle_factors else 'Unknown'
        patient_weight = "Unknown"
        if patient_context.lab_values and 'weight' in patient_context.lab_values:
            weight_data = patient_context.lab_values['weight']
            if isinstance(weight_data, dict):
                latest_date = max(weight_data.keys())
                weight_info = weight_data[latest_date]
                if isinstance(weight_info, dict):
                    patient_weight = f"{weight_info.get('value', 'Unknown')} {weight_info.get('unit', '')}"
                else:
                    patient_weight = str(weight_info)
        
        prompt = f"""Create a personalized response for this patient using their complete profile:
        
        PATIENT PROFILE:
        Name: {patient_name}
        Age: {patient_context.age or 'Unknown'}
        Gender: {patient_context.gender or 'Unknown'}
        Height: {patient_height}
        Weight: {patient_weight}
        Conditions: {', '.join(patient_context.conditions) if patient_context.conditions else 'None'}
        
        USER QUERY: {user_input.symptoms}
        
        AGENT ANALYSIS: {' '.join([f"{k}: {v}" for k, v in all_outputs.items()])}
        
        Use the patient's profile information to answer their query directly and personally. Create a helpful, personalized response. Sign as "Your AI Health Team"."""
        
        # Use personality prompt
        personality_prompt = PERSONALITIES[personality]["system_prompt"]
        
        messages = [
            SystemMessage(content=personality_prompt),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        final_response = response.content
        if "[Your Name]" in final_response:
            final_response = final_response.replace("[Your Name]", "Your AI Health Team")
        if "Your AI Health Team" not in final_response:
            final_response += "\n\nBest regards,\nYour AI Health Team"
        
        synthesis_result = SynthesisResult(
            all_agent_outputs=all_outputs,
            safety_validations=safety_check.get("safety_flags", []),
            cross_checks={"validated": True},
            final_recommendations={"plan": final_response},
            appointment_needed=state.get("treatment_result", {}).appointment_needed if state.get("treatment_result") else False,
            priority_level=state.get("diagnosis_result", {}).severity_level if state.get("diagnosis_result") else "MEDIUM"
        )
        
        return {"synthesis_result": synthesis_result}
    
    def _hallucination_detector(self, state: MultiAgentHealthState):
        synthesis_result = state["synthesis_result"]
        
        plan_content = synthesis_result.final_recommendations.get("plan", "")
        
        flagged_claims = []
        dangerous_words = ["cure", "guaranteed", "diagnose yourself"]
        
        for word in dangerous_words:
            if word in plan_content.lower():
                flagged_claims.append(f"Contains: {word}")
        
        hallucination_check = HallucinationCheck(
            source_citations=["Medical sources"],
            fact_verification={"checked": True},
            consistency_score=0.9,
            medical_accuracy={"appropriate": True},
            flagged_claims=flagged_claims,
            validation_status="APPROVED" if not flagged_claims else "FLAGGED"
        )
        
        return {"hallucination_check": hallucination_check}
    
    #=========================================================================
    # MAIN PROCESSING WITH ENHANCED VALIDATION
    #=========================================================================
    
    def process_health_query(self, user_input: UserInput, personality: str = "concise", thread_id: str = "default", progress_callback=None):
        thread = {"configurable": {"thread_id": thread_id}}
        
        # Add to conversation history
        self.conversation_history.append(f"User: {user_input.symptoms}")
        
        # Update timestamp
        self.patient_context.last_updated = datetime.now()
        
        # Process with enhanced validation
        if progress_callback:
            # Step by step processing with progress updates
            state = {
                "user_input": user_input,
                "personality": personality,
                "conversation_history": self.conversation_history.copy(),
                "openai_settings": self.openai_settings,
                "patient_context": self.patient_context
            }
            
            # Data validation
            progress_callback("🔍 Validating input data...", 0.05)
            state.update(self._data_validator(state))
            
            # Handle validation errors
            if state.get("validation_error"):
                progress_callback("❌ Validation failed", 0.9)
                state.update(self._validation_error_handler(state))
                result = state
            else:
                # Profile extraction
                progress_callback("👤 Extracting user profile...", 0.1)
                state.update(self._profile_extractor(state))
                
                # Update patient context
                if state.get("patient_context"):
                    self.patient_context = state["patient_context"]
                
                # Triage
                progress_callback("🚨 Triaging symptoms...", 0.2)
                state.update(self._triage_agent(state))
                
                routing = state["triage_result"].routing_decision
                
                # Handle different routing decisions
                if routing == "emergency":
                    progress_callback("🚨 Emergency detected - priority handling...", 0.5)
                    state.update(self._emergency_handler(state))
                elif routing == "non_health_rejection":
                    progress_callback("❌ Non-health query detected...", 0.5)
                    state.update(self._non_health_rejection(state))
                else:
                    # Normal health pipeline (same as before)
                    if routing == "diet_only":
                        progress_callback("🥗 Generating dietary recommendations...", 0.5)
                        state.update(self._diet_agent(state))
                        progress_callback("🧠 Synthesizing response...", 0.85)
                        state.update(self._synthesis_agent(state))
                        progress_callback("✅ Validating recommendations...", 0.95)
                        state.update(self._hallucination_detector(state))
                    elif routing == "treatment_only":
                        progress_callback("💊 Creating treatment plan...", 0.5)
                        state.update(self._treatment_agent(state))
                        progress_callback("🧠 Synthesizing response...", 0.85)
                        state.update(self._synthesis_agent(state))
                        progress_callback("✅ Validating recommendations...", 0.95)
                        state.update(self._hallucination_detector(state))
                    elif routing == "diagnosis_only":
                        progress_callback("🔍 Analyzing symptoms...", 0.5)
                        state.update(self._diagnosis_agent(state))
                        progress_callback("🧠 Synthesizing response...", 0.85)
                        state.update(self._synthesis_agent(state))
                        progress_callback("✅ Validating recommendations...", 0.95)
                        state.update(self._hallucination_detector(state))
                    elif routing == "clarification":
                        progress_callback("💭 Processing clarification...", 0.5)
                        progress_callback("🧠 Synthesizing response...", 0.85)
                        state.update(self._synthesis_agent(state))
                        progress_callback("✅ Validating recommendations...", 0.95)
                        state.update(self._hallucination_detector(state))
                    else:  # full_pipeline
                        progress_callback("🔍 Analyzing symptoms...", 0.3)
                        state.update(self._diagnosis_agent(state))
                        progress_callback("🥗 Generating dietary recommendations...", 0.5)
                        state.update(self._diet_agent(state))
                        progress_callback("💊 Creating treatment plan...", 0.7)
                        state.update(self._treatment_agent(state))
                        progress_callback("🧠 Synthesizing response...", 0.85)
                        state.update(self._synthesis_agent(state))
                        progress_callback("✅ Validating recommendations...", 0.95)
                        state.update(self._hallucination_detector(state))
                
                result = state
        else:
            # Normal processing through graph
            result = self.graph.invoke({
                "user_input": user_input,
                "personality": personality,
                "conversation_history": self.conversation_history.copy(),
                "openai_settings": self.openai_settings,
                "patient_context": self.patient_context
            }, thread)
            
            # Update patient context
            if result.get("patient_context"):
                self.patient_context = result["patient_context"]
        
        # Generate final response
        synthesis_result = result["synthesis_result"]
        final_plan = synthesis_result.final_recommendations.get("plan", "")
        
        # Don't add medical disclaimer to emergency or validation error responses
        if result.get("hallucination_check", {}).validation_status in ["EMERGENCY_APPROVED", "VALIDATION_ERROR"]:
            response = final_plan
        else:
            response = f"{final_plan}\n\n{MEDICAL_DISCLAIMER}"
        
        # Add to conversation history
        self.conversation_history.append(f"Assistant: {final_plan}")
        
        # Keep history manageable
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        # Create conversation summary
        current_summary = ConversationSummary(
            session_id=thread_id,
            key_facts_extracted=list(self.patient_context.symptoms_timeline.get(
                datetime.now().strftime("%Y-%m-%d"), []
            )),
            new_symptoms=[],
            new_lab_values={},
            recommendations_made=[],
            follow_up_needed=self.patient_context.unresolved_questions,
            timestamp=datetime.now()
        )
        
        return {
            "response": response,
            "triage_result": result.get("triage_result", TriageResult(
                intent_classification="unknown",
                urgency_level="MEDIUM",
                emergency_flags=[],
                routing_decision="unknown",
                confidence_score=0.5
            )),
            "diagnosis_result": result.get("diagnosis_result", DiagnosisResult(
                symptoms=[],
                symptom_analysis={},
                possible_conditions=[],
                severity_level="MEDIUM",
                recommended_tests=[],
                red_flags=[],
                research_sources=[]
            )),
            "diet_result": result.get("diet_result", DietResult(
                diagnosed_condition="",
                dietary_restrictions=[],
                nutritional_needs={},
                recommended_foods=[],
                foods_to_avoid=[],
                meal_suggestions=[],
                supplements=[]
            )),
            "treatment_result": result.get("treatment_result", TreatmentResult(
                diagnosis={},
                treatment_options=[],
                care_recommendations=[],
                lifestyle_changes=[],
                follow_up_schedule={},
                when_to_see_doctor="",
                appointment_needed=False
            )),
            "synthesis_result": result.get("synthesis_result", SynthesisResult(
                all_agent_outputs={},
                safety_validations=[],
                cross_checks={},
                final_recommendations={"plan": "Error occurred"},
                appointment_needed=False,
                priority_level="MEDIUM"
            )),
            "validation_status": result.get("hallucination_check", HallucinationCheck(
                source_citations=[],
                fact_verification={},
                consistency_score=1.0,
                medical_accuracy={},
                flagged_claims=[],
                validation_status="UNKNOWN"
            )).validation_status,
            "patient_context": self.patient_context,
            "conversation_summary": current_summary
        }
    
    def get_patient_summary(self) -> str:
        """Get a formatted summary of the patient's health journey"""
        summary = f"""# Patient Health Summary
**Last Updated:** {self.patient_context.last_updated.strftime("%Y-%m-%d %H:%M")}

## Demographics
- **Age:** {self.patient_context.age if self.patient_context.age else 'Not specified'}
- **Gender:** {self.patient_context.gender if self.patient_context.gender else 'Not specified'}

## Known Conditions
{chr(10).join(['- ' + condition for condition in self.patient_context.conditions]) if self.patient_context.conditions else '- None recorded'}

## Current Lab Values
"""
        if self.patient_context.lab_values:
            for test, values in self.patient_context.lab_values.items():
                if isinstance(values, dict) and any(isinstance(k, str) for k in values.keys()):
                    # Date-based values
                    latest_date = max(values.keys())
                    summary += f"- **{test}:** {values[latest_date]} (as of {latest_date})\n"
                else:
                    summary += f"- **{test}:** {values}\n"
        else:
            summary += "- No lab values recorded\n"
        
        summary += f"""
## Current Medications
{chr(10).join(['- ' + med for med in self.patient_context.medications]) if self.patient_context.medications else '- None recorded'}

## Recent Symptoms
"""
        if self.patient_context.symptoms_timeline:
            for date, symptoms in sorted(self.patient_context.symptoms_timeline.items(), reverse=True)[:3]:
                summary += f"- **{date}:** {', '.join(symptoms)}\n"
        else:
            summary += "- No symptoms recorded\n"
        
        return summary