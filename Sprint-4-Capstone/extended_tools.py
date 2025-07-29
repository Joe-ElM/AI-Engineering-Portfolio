import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config import TAVILY_API_KEY

try:
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError:
    TavilySearchResults = None
from langchain_community.document_loaders import WikipediaLoader


#=============================================================================
# RESEARCH TOOLS (KEEP THESE - THEY WORK WELL)
#=============================================================================

@tool
def search_wikipedia(query: str, max_docs: int = 2) -> str:
    """Search Wikipedia for medical information"""
    try:
        search_query = f"{query} medical symptoms causes treatment"
        loader = WikipediaLoader(query=search_query, load_max_docs=max_docs)
        docs = loader.load()
        
        formatted_docs = "\n\n---\n\n".join([
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in docs
        ])
        
        return formatted_docs
        
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

@tool
def search_tavily(query: str, max_results: int = 3) -> str:
    """Search web using Tavily for current medical information"""
    try:
        if not TAVILY_API_KEY:
            return "Tavily search unavailable - API key not configured"
            
        tavily_search = TavilySearchResults(
            max_results=max_results,
            api_key=TAVILY_API_KEY
        )
        
        search_query = f"{query} symptoms medical information causes treatment"
        search_docs = tavily_search.invoke(search_query)
        
        formatted_docs = "\n\n---\n\n".join([
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ])
        
        return formatted_docs
        
    except Exception as e:
        return f"Error searching Tavily: {str(e)}"

#=============================================================================
# SIMPLE CALCULATION TOOLS (KEEP THESE)
#=============================================================================

@tool
def calculate_bmi(height_cm: float, weight_kg: float) -> Dict[str, any]:
    """Calculate BMI and provide health category"""
    try:
        if height_cm <= 0 or weight_kg <= 0:
            return {"error": "Invalid height or weight values"}
        
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal weight"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
        
        return {
            "bmi": round(bmi, 1),
            "category": category,
            "healthy_range": "18.5 - 24.9"
        }
        
    except Exception as e:
        return {"error": f"BMI calculation error: {str(e)}"}

@tool
def calculate_nutrition_needs(condition: str, age: int, gender: str, activity_level: str) -> Dict[str, any]:
    """Calculate basic nutritional needs based on condition and demographics"""
    try:
        # Base caloric needs (simplified calculation)
        if gender.lower() == "male":
            bmr = 88.362 + (13.397 * 70) + (4.799 * 175) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * 60) + (3.098 * 165) - (4.330 * age)
        
        activity_multiplier = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725
        }.get(activity_level.lower(), 1.55)
        
        daily_calories = int(bmr * activity_multiplier)
        
        # Condition-specific notes
        condition_notes = {}
        condition_lower = condition.lower()
        
        if "diabetes" in condition_lower:
            condition_notes["carbohydrates"] = "Focus on complex carbs, limit simple sugars"
        if "hypertension" in condition_lower or "high blood pressure" in condition_lower:
            condition_notes["sodium"] = "Limit to under 2300mg daily"
        if "heart" in condition_lower:
            condition_notes["fats"] = "Focus on healthy fats, limit saturated fats"
        if "kidney" in condition_lower:
            condition_notes["protein"] = "May need protein restriction - consult doctor"
        if "liver" in condition_lower:
            condition_notes["alcohol"] = "Avoid alcohol completely"
        
        return {
            "daily_calories": daily_calories,
            "condition_notes": condition_notes
        }
        
    except Exception as e:
        return {"error": f"Nutrition calculation error: {str(e)}"}

@tool
def score_symptom_severity(symptoms: List[str], age: int = None) -> Dict[str, any]:
    """Score symptom severity based on common medical criteria"""
    try:
        emergency_keywords = [
            "chest pain", "difficulty breathing", "severe bleeding", 
            "unconscious", "seizure", "stroke", "heart attack"
        ]
        
        high_severity = [
            "fever over 101", "persistent vomiting", "severe headache",
            "confusion", "rapid heartbeat", "shortness of breath"
        ]
        
        symptom_text = " ".join(symptoms).lower()
        score = 0
        
        # Check for emergency symptoms
        for keyword in emergency_keywords:
            if keyword in symptom_text:
                score += 10
        
        # Check for high severity symptoms
        for keyword in high_severity:
            if keyword in symptom_text:
                score += 5
        
        # Age factor
        if age and (age > 65 or age < 5):
            score += 2
        
        # Determine severity level
        if score >= 10:
            level = "EMERGENCY"
        elif score >= 7:
            level = "HIGH"
        elif score >= 4:
            level = "MODERATE"
        else:
            level = "LOW"
        
        return {
            "severity_score": score,
            "severity_level": level
        }
        
    except Exception as e:
        return {"error": f"Severity scoring error: {str(e)}"}

@tool
def schedule_appointment(urgency: str, condition: str, preferred_timeframe: str) -> Dict[str, any]:
    """Generate appointment scheduling recommendation"""
    try:
        urgency_mapping = {
            "emergency": {"timeframe": "Immediate", "provider": "Emergency Room"},
            "high": {"timeframe": "Within 3-5 days", "provider": "Primary Care"},
            "moderate": {"timeframe": "Within 1-2 weeks", "provider": "Primary Care"},
            "low": {"timeframe": "Within 4 weeks", "provider": "Primary Care"}
        }
        
        appointment_info = urgency_mapping.get(urgency.lower(), urgency_mapping["moderate"])
        
        return {
            "recommended_timeframe": appointment_info["timeframe"],
            "provider_type": appointment_info["provider"],
            "scheduling_note": f"For {condition}: {preferred_timeframe}"
        }
        
    except Exception as e:
        return {"error": f"Appointment scheduling error: {str(e)}"}

@tool
def validate_medical_safety(recommendations: Dict[str, any], user_profile: Dict[str, any] = None) -> Dict[str, any]:
    """Simple safety validation"""
    try:
        safety_flags = []
        warnings = []
        
        rec_text = str(recommendations).lower()
        
        # Check for dangerous self-medication advice
        if "medication" in rec_text and ("adjust" in rec_text or "stop" in rec_text):
            safety_flags.append("Contains medication change advice - requires professional oversight")
        
        # Check age-related concerns
        if user_profile and user_profile.get("age", 0) > 65:
            warnings.append("Elderly patients may have different risk factors")
        
        validation_status = "APPROVED" if not safety_flags else "FLAGGED"
        
        return {
            "validation_status": validation_status,
            "safety_flags": safety_flags,
            "warnings": warnings
        }
        
    except Exception as e:
        return {"error": f"Safety validation error: {str(e)}"}

def combine_search_results(wikipedia_results: str, tavily_results: str) -> str:
    """Combine and format search results from multiple sources"""
    combined = []
    
    if wikipedia_results and "Error" not in wikipedia_results:
        combined.append("## Wikipedia Sources:\n" + wikipedia_results)
    
    if tavily_results and "Error" not in tavily_results:
        combined.append("## Web Sources:\n" + tavily_results)
    
    if not combined:
        return "No reliable medical information found. Please consult a healthcare professional."
    
    return "\n\n".join(combined)