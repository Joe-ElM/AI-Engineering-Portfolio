from typing import List, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class UserInput(BaseModel):
    symptoms: str = Field(description="User's described symptoms")
    age: Optional[int] = Field(description="User's age")
    gender: Optional[str] = Field(description="User's gender")

class HealthAgentState(TypedDict):
    user_input: UserInput
    research_content: str
    response: str
    personality: str
    conversation_history: List[str]
    openai_settings: Dict[str, float]
