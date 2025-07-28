from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

class Agent:
    def __init__(self, name, role, instructions, tools, model="gpt-4o-mini", temperature=0.0):
        llm = ChatOpenAI(model=model, temperature=temperature)
        self.agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=False
        )
    
    def invoke(self, user_message):
        result = self.agent.run(user_message)
        
        return result
    