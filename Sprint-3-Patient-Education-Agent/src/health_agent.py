from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from schemas import HealthAgentState, UserInput
from tools import search_wikipedia, search_tavily, combine_search_results
from config import PERSONALITIES, HEALTH_PROMPT, MEDICAL_DISCLAIMER

class HealthAgent:
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
    
    def _build_graph(self):
        builder = StateGraph(HealthAgentState)
        
        builder.add_node("research_symptoms", self._research_symptoms)
        builder.add_node("generate_response", self._generate_response)
        
        builder.add_edge(START, "research_symptoms")
        builder.add_edge("research_symptoms", "generate_response")
        builder.add_edge("generate_response", END)
        
        return builder.compile(checkpointer=self.memory)
    
    def _research_symptoms(self, state: HealthAgentState):
        user_input = state["user_input"]
        symptoms = user_input.symptoms
        
        wikipedia_results = search_wikipedia(symptoms)
        tavily_results = search_tavily(symptoms)
        research_content = combine_search_results(wikipedia_results, tavily_results)
        
        return {"research_content": research_content}
    
    def _generate_response(self, state: HealthAgentState):
        user_input = state["user_input"]
        research_content = state["research_content"]
        personality = state.get("personality", "friendly")
        conversation_history = state.get("conversation_history", [])
        
        system_prompt = PERSONALITIES[personality]
        
        # Add conversation context
        context = ""
        if conversation_history:
            context = f"Previous conversation:\n{chr(10).join(conversation_history[-6:])}\n\n"
        
        health_prompt = HEALTH_PROMPT.format(
            symptoms=user_input.symptoms,
            age=user_input.age or "Not specified", 
            gender=user_input.gender or "Not specified",
            research_content=research_content
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context + health_prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Update conversation history
        new_history = conversation_history + [
            f"User: {user_input.symptoms}",
            f"Assistant: {response.content[:200]}..."
        ]
        
        return {
            "response": response.content + "\n\n" + MEDICAL_DISCLAIMER,
            "conversation_history": new_history
        }
    
    def process_symptoms(self, user_input: UserInput, personality: str = "friendly", thread_id: str = "default"):
        thread = {"configurable": {"thread_id": thread_id}}
        
        result = self.graph.invoke({
            "user_input": user_input,
            "personality": personality,
            "openai_settings": self.openai_settings
        }, thread)
        
        return result