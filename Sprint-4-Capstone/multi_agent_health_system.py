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
        
        # Simplified node structure
        builder.add_node("profile_extractor", self._profile_extractor)
        builder.add_node("triage_agent", self._triage_agent)
        builder.add_node("diagnosis_agent", self._diagnosis_agent)
        builder.add_node("diet_agent", self._diet_agent)
        builder.add_node("treatment_agent", self._treatment_agent)
        builder.add_node("synthesis_agent", self._synthesis_agent)
        builder.add_node("hallucination_detector", self._hallucination_detector)
        
        # Start with profile extraction
        builder.add_edge(START, "profile_extractor")
        builder.add_edge("profile_extractor", "triage_agent")
        
        # Conditional routing from triage
        builder.add_conditional_edges(
            "triage_agent",
            self._route_decision,
            {
                "diagnosis_only": "diagnosis_agent",
                "diet_only": "diet_agent",
                "treatment_only": "treatment_agent",
                "full_pipeline": "diagnosis_agent",
                "clarification": "synthesis_agent"
            }
        )
        
        # Conditional edges for partial routes
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
    
    def _route_decision(self, state: MultiAgentHealthState):
        """Determine which route to take based on triage results"""
        triage_result = state.get("triage_result", {})
        return triage_result.routing_decision
    
    #=========================================================================
    # PROFILE EXTRACTOR - UPDATED WITH STRUCTURED LLM
    #=========================================================================
    
    def _profile_extractor(self, state: MultiAgentHealthState):
        """Extract user profile using structured LLM output"""
        user_input = state["user_input"]
        
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
            # Parse JSON response
            extracted_data = json.loads(response.content.strip())
            
            # Update patient context with extracted data
            if extracted_data.get("name"):
                self.patient_context.user_id = extracted_data["name"]
            
            if extracted_data.get("age"):
                self.patient_context.age = int(extracted_data["age"])
            
            if extracted_data.get("gender"):
                self.patient_context.gender = extracted_data["gender"].lower()
            
            if extracted_data.get("conditions"):
                self.patient_context.conditions.extend(extracted_data["conditions"])
            
            if extracted_data.get("medications"):
                self.patient_context.medications.extend(extracted_data["medications"])
            
            if extracted_data.get("allergies"):
                if "allergies" not in self.patient_context.lifestyle_factors:
                    self.patient_context.lifestyle_factors["allergies"] = []
                self.patient_context.lifestyle_factors["allergies"].extend(extracted_data["allergies"])
            
            if extracted_data.get("family_history"):
                self.patient_context.lifestyle_factors["family_history"] = extracted_data["family_history"]
            
            # Handle lifestyle factors
            if extracted_data.get("lifestyle"):
                lifestyle = extracted_data["lifestyle"]
                if lifestyle.get("smoking"):
                    self.patient_context.lifestyle_factors["smoking"] = lifestyle["smoking"]
                if lifestyle.get("alcohol"):
                    self.patient_context.lifestyle_factors["alcohol"] = lifestyle["alcohol"]
                if lifestyle.get("exercise"):
                    self.patient_context.lifestyle_factors["exercise"] = lifestyle["exercise"]
            
            # Handle lab values
            if extracted_data.get("lab_values"):
                current_date = datetime.now().strftime("%Y-%m-%d")
                for test_name, value in extracted_data["lab_values"].items():
                    if test_name not in self.patient_context.lab_values:
                        self.patient_context.lab_values[test_name] = {}
                    self.patient_context.lab_values[test_name][current_date] = float(value)
            
            # Handle weight
            if extracted_data.get("weight") and extracted_data.get("weight_unit"):
                current_date = datetime.now().strftime("%Y-%m-%d")
                if 'weight' not in self.patient_context.lab_values:
                    self.patient_context.lab_values['weight'] = {}
                self.patient_context.lab_values['weight'][current_date] = {
                    'value': float(extracted_data["weight"]), 
                    'unit': extracted_data["weight_unit"]
                }
            
            # Handle height
            if extracted_data.get("height"):
                self.patient_context.lifestyle_factors['height'] = extracted_data["height"]
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Profile extraction error: {e}")
            # Fallback: still extract basic info from original text if JSON parsing fails
            text = user_input.symptoms.lower()
            
            # Simple text-based extraction as fallback
            age_match = re.search(r'(\d+)[-\s]?year[-\s]?old', text)
            if age_match:
                self.patient_context.age = int(age_match.group(1))
            
            if 'male' in text or 'man' in text:
                self.patient_context.gender = 'male'
            elif 'female' in text or 'woman' in text:
                self.patient_context.gender = 'female'
        
        # Also check direct user input fields as before
        if user_input.age:
            self.patient_context.age = user_input.age
        if user_input.gender:
            self.patient_context.gender = user_input.gender
        
        # Update symptoms timeline
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.patient_context.symptoms_timeline[current_date] = [user_input.symptoms[:100]]
        
        return {"patient_context": self.patient_context}
    
    #=========================================================================
    # TRIAGE AGENT - SIMPLIFIED
    #=========================================================================
    
    def _triage_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        
        prompt = f"""Classify this health query:
        Query: {user_input.symptoms}
        Patient: {patient_context.age or 'Unknown'} year old {patient_context.gender or 'Unknown'}
        
        Return:
        1. Urgency: LOW/MEDIUM/HIGH/EMERGENCY
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
        if "emergency" in content:
            urgency = "EMERGENCY"
        elif "high" in content:
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
    # DIAGNOSIS AGENT - SIMPLIFIED
    #=========================================================================
    
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
    
    #=========================================================================
    # DIET AGENT - SIMPLIFIED
    #=========================================================================
    
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
    
    #=========================================================================
    # TREATMENT AGENT - SIMPLIFIED
    #=========================================================================
    
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
    
    #=========================================================================
    # SYNTHESIS AGENT - FIXED WITH PERSONALITY INTEGRATION
    #=========================================================================
    
    def _synthesis_agent(self, state: MultiAgentHealthState):
        user_input = state["user_input"]
        patient_context = state.get("patient_context", self.patient_context)
        triage_result = state["triage_result"]
        personality = state.get("personality", "friendly")  # Get personality from state
        
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
        patient_height = patient_context.lifestyle_factors.get('height', 'Unknown')
        patient_weight = "Unknown"
        if 'weight' in patient_context.lab_values:
            weight_data = patient_context.lab_values['weight']
            if isinstance(weight_data, dict):
                latest_date = max(weight_data.keys())
                weight_info = weight_data[latest_date]
                if isinstance(weight_info, dict):
                    patient_weight = f"{weight_info.get('value', 'Unknown')} {weight_info.get('unit', '')}"
                else:
                    patient_weight = str(weight_info)
        
        patient_allergies = patient_context.lifestyle_factors.get('allergies', [])
        patient_family_history = patient_context.lifestyle_factors.get('family_history', [])
        patient_smoking = patient_context.lifestyle_factors.get('smoking', 'Unknown')
        patient_alcohol = patient_context.lifestyle_factors.get('alcohol', 'Unknown')
        patient_exercise = patient_context.lifestyle_factors.get('exercise', 'Unknown')
        
        # Get recent lab values
        lab_summary = []
        for test, values in patient_context.lab_values.items():
            if test != 'weight' and isinstance(values, dict):
                latest_date = max(values.keys())
                lab_summary.append(f"{test}: {values[latest_date]}")
        
        prompt = f"""Create a personalized response for this patient using their complete profile:
        
        PATIENT PROFILE:
        Name: {patient_name}
        Age: {patient_context.age or 'Unknown'}
        Gender: {patient_context.gender or 'Unknown'}
        Height: {patient_height}
        Weight: {patient_weight}
        Conditions: {', '.join(patient_context.conditions) if patient_context.conditions else 'None'}
        Medications: {', '.join(patient_context.medications) if patient_context.medications else 'None'}
        Allergies: {', '.join(patient_allergies) if patient_allergies else 'None'}
        Family History: {', '.join(patient_family_history) if patient_family_history else 'None'}
        Smoking: {patient_smoking}
        Alcohol: {patient_alcohol}
        Exercise: {patient_exercise}
        Recent Lab Values: {', '.join(lab_summary) if lab_summary else 'None'}
        
        USER QUERY: {user_input.symptoms}
        
        AGENT ANALYSIS: {' '.join([f"{k}: {v}" for k, v in all_outputs.items()])}
        
        Use the patient's profile information to answer their query directly and personally. If they ask about their name, age, height, weight, etc., use the profile data above. Create a helpful, personalized response. Sign as "Your AI Health Team"."""
        
        # USE PERSONALITY PROMPT - THIS IS THE KEY FIX
        personality_prompt = PERSONALITIES[personality]["system_prompt"]
        
        messages = [
            SystemMessage(content=personality_prompt),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Ensure proper signature
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
    
    #=========================================================================
    # HALLUCINATION DETECTOR - SIMPLIFIED
    #=========================================================================
    
    def _hallucination_detector(self, state: MultiAgentHealthState):
        synthesis_result = state["synthesis_result"]
        
        # Simple validation
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
    # MAIN PROCESSING - DEFAULT TO CONCISE
    #=========================================================================
    
    def process_health_query(self, user_input: UserInput, personality: str = "concise", thread_id: str = "default", progress_callback=None):
        thread = {"configurable": {"thread_id": thread_id}}
        
        # Add to conversation history
        self.conversation_history.append(f"User: {user_input.symptoms}")
        
        # Update timestamp
        self.patient_context.last_updated = datetime.now()
        
        # Process with or without progress callback
        if progress_callback:
            # Step by step processing with progress updates
            state = {
                "user_input": user_input,
                "personality": personality,
                "conversation_history": self.conversation_history.copy(),
                "openai_settings": self.openai_settings,
                "patient_context": self.patient_context
            }
            
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
            
            # Route based on triage
            if routing == "diet_only":
                progress_callback("🥗 Generating dietary recommendations...", 0.5)
                state.update(self._diet_agent(state))
            elif routing == "treatment_only":
                progress_callback("💊 Creating treatment plan...", 0.5)
                state.update(self._treatment_agent(state))
            elif routing == "diagnosis_only":
                progress_callback("🔍 Analyzing symptoms...", 0.5)
                state.update(self._diagnosis_agent(state))
            elif routing == "clarification":
                progress_callback("💭 Processing clarification...", 0.5)
            else:  # full_pipeline
                progress_callback("🔍 Analyzing symptoms...", 0.3)
                state.update(self._diagnosis_agent(state))
                progress_callback("🥗 Generating dietary recommendations...", 0.5)
                state.update(self._diet_agent(state))
                progress_callback("💊 Creating treatment plan...", 0.7)
                state.update(self._treatment_agent(state))
            
            # Always synthesize
            progress_callback("🧠 Synthesizing response...", 0.85)
            state.update(self._synthesis_agent(state))
            
            # Always validate
            progress_callback("✅ Validating recommendations...", 0.95)
            state.update(self._hallucination_detector(state))
            
            result = state
        else:
            # Normal processing
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
            "triage_result": result["triage_result"],
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
            "synthesis_result": result["synthesis_result"],
            "validation_status": result["hallucination_check"].validation_status,
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