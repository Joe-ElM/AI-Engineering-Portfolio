# HealthBot - AI-Powered Patient Education Agent

A conversational AI agent that provides educational health information and symptom awareness through intelligent research and personalized responses.

## Overview

HealthBot is an educational AI assistant built with LangGraph that helps users understand symptoms, learn about health conditions, and receive guidance on when to seek medical care. The system combines Wikipedia and Tavily search capabilities to provide comprehensive, research-backed health education.

**Important Disclaimer**: This application is for educational purposes only and does not provide medical advice. Always consult qualified healthcare professionals for medical concerns.

## Features

- Symptom analysis and educational information
- Multi-source research (Wikipedia + Tavily)
- Conversation memory and context awareness
- Customizable AI personality (friendly, formal, concise)
- Adjustable AI parameters (temperature, top-p)
- Supplement and vitamin recommendations
- Emergency vs routine care guidance
- Chat-style interface with source transparency

## Technology Stack

- **LangGraph**: Workflow orchestration and state management
- **OpenAI GPT-4o-mini**: Natural language processing
- **Streamlit**: Web interface
- **Wikipedia API**: Medical reference information
- **Tavily API**: Current web search capabilities
- **Pydantic**: Data validation and schemas

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create environment file:

```bash
cp .env.example .env
```

3. Add your API keys to `.env`:

```
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

## Usage

### Running the Application

Start the Streamlit interface:

```bash
streamlit run src/main.py
```

Access the application at `http://localhost:8501`

### Configuration Options

**Personality Settings**:

- Friendly: Warm, caring communication style
- Formal: Professional, clinical information delivery
- Concise: Direct, efficient responses

**AI Parameters**:

- Temperature (0.0-1.0): Controls response creativity
- Top-p (0.0-1.0): Controls response focus vs diversity
- Max tokens (100-2000): Response length limit

## Sample Interactions

### Symptom Analysis

```
User: "I have been experiencing headaches and fatigue for 3 days"

HealthBot: Based on your symptoms, here are the most likely causes:

1. Dehydration or insufficient sleep
2. Viral infection (common cold, flu)
3. Stress or tension headaches

When to seek care:
- Routine: If symptoms persist beyond a week
- Urgent: Severe headache with fever or vision changes

Recommendations:
- Stay hydrated and maintain regular sleep schedule
- Consider magnesium supplementation
- Monitor for worsening symptoms
```

### Supplement Queries

```
User: "What vitamins help boost immune system?"

HealthBot: Key immune-supporting supplements include:

1. Vitamin D3 (1000-4000 IU daily)
2. Vitamin C (500-1000mg daily)
3. Zinc (8-11mg daily)

These support immune function when combined with proper diet and sleep. Consult healthcare providers before starting new supplements.
```

### Follow-up Questions

```
User: "What should I do if the headache gets worse?"

HealthBot: If your headache worsens, consider these steps:

1. Seek urgent care if accompanied by fever, stiff neck, or vision changes
2. Emergency care for sudden severe headache or loss of consciousness
3. Track symptoms and potential triggers

Contact healthcare provider if pain becomes severe or doesn't respond to over-the-counter treatments.
```

## Project Structure

```
patient-education-agent/
├── src/
│   ├── main.py           # Streamlit application
│   ├── health_agent.py   # Core agent logic
│   ├── tools.py          # Search functions
│   ├── config.py         # Settings and prompts
│   └── schemas.py        # Data models
├── requirements.txt      # Dependencies
├── .env.example         # Environment template
└── README.md           # Documentation
```

## API Requirements

### OpenAI API

- Required for natural language processing
- GPT-4o-mini model recommended
- Obtain key from https://platform.openai.com

### Tavily API

- Optional but recommended for current web search
- Enhances research capabilities
- Obtain key from https://tavily.com

## Safety Features

- Prominent medical disclaimers on all responses
- Clear distinction between educational content and medical advice
- Emergency situation identification and guidance
- Source transparency for all medical information
- Non-health query filtering and redirection

## Code Examples

### Basic Agent Usage

```python
from src.health_agent import HealthAgent
from src.schemas import UserInput

# Initialize agent with custom settings
settings = {"temperature": 0.7, "top_p": 0.9, "max_tokens": 800}
agent = HealthAgent(openai_settings=settings)

# Process symptoms
user_input = UserInput(
    symptoms="joint pain in knees when walking",
    age=45,
    gender="female"
)
result = agent.process_symptoms(user_input, personality="formal")
print(result["response"])
```

### Search Tools Testing

```python
from src.tools import search_wikipedia, search_tavily, combine_search_results

# Test individual search functions
wiki_results = search_wikipedia("vitamin D deficiency")
tavily_results = search_tavily("vitamin D deficiency symptoms")
combined = combine_search_results(wiki_results, tavily_results)
print(combined[:500])
```

### Memory and Conversation Flow

```python
# Test conversation memory
agent = HealthAgent()

# First interaction
input1 = UserInput(symptoms="frequent headaches")
result1 = agent.process_symptoms(input1, thread_id="patient_001")

# Follow-up with memory
input2 = UserInput(symptoms="what supplements help with this?")
result2 = agent.process_symptoms(input2, thread_id="patient_001")
# Agent remembers previous headache context
```

### Custom Configuration

```python
# Modify agent behavior in config.py
PERSONALITIES = {
    "clinical": "You are a clinical health educator providing medical-grade information.",
    "pediatric": "You are a pediatric health educator specializing in children's health."
}

# Test different personalities
result_clinical = agent.process_symptoms(user_input, "clinical")
result_pediatric = agent.process_symptoms(user_input, "pediatric")
```

### Advanced Testing

```python
# Test health vs non-health detection
test_cases = [
    "I have chest pain",           # Health - should analyze
    "weather forecast today",      # Non-health - should redirect
    "vitamin C dosage",           # Health - should provide info
    "stock market trends"         # Non-health - should redirect
]

for case in test_cases:
    input_test = UserInput(symptoms=case)
    result = agent.process_symptoms(input_test)
    print(f"Input: {case}")
    print(f"Response: {result['response'][:100]}...\n")
```

## Jupyter Notebook

For comprehensive examples, testing scenarios, and technical documentation, see `project.ipynb`. The notebook includes:

- Complete implementation walkthrough
- Interactive testing cells
- Workflow diagram visualization
- Memory demonstration
- Error handling examples
- Performance optimization tips

Run the notebook for hands-on exploration:

```bash
jupyter lab project.ipynb
```

### Customizing Prompts

Modify `src/config.py` to adjust:

- Agent personalities
- Medical disclaimers
- Response formatting
- Safety guidelines

## Project Assessment Level

This project meets **Medium Level** criteria according to Turing College requirements:

### What This Project Includes

**Core Functionality (Easy Level)**:

- AI agent with clear health education purpose
- OpenAI API integration for natural language processing
- Streamlit web interface with intuitive design
- Wikipedia and Tavily API integrations
- Proper error handling and validation

**Advanced Features (Medium Level)**:

- LangGraph workflow orchestration with state management
- Conversation memory using MemorySaver checkpointer
- Multiple function tools (Wikipedia + Tavily search)
- Agent personality customization (friendly/formal/concise)
- OpenAI parameter controls (temperature, top-p, max tokens)
- Multi-source research synthesis
- Context-aware follow-up conversations

**Safety and Quality**:

- Medical disclaimers and safety warnings
- Non-health query filtering
- Source transparency and citation
- Emergency vs routine care guidance
- Modular, maintainable code architecture

### What This Project Does Not Include

**Hard Level Features**:

- RAG with document database/vector store
- Multi-agent collaboration system
- Advanced routing with complex decision trees
- Fine-tuned models for specific domains
- Cloud deployment with scaling
- LLM observability tools integration
- Large dataset processing capabilities

The project demonstrates solid understanding of AI agents, LangGraph workflows, and practical application development while maintaining focus on educational health information delivery.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with appropriate tests
4. Submit pull request with clear description

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built for Turing College Sprint 3 AI Agent Development project. Demonstrates integration of LangGraph, OpenAI, and multi-source research capabilities for educational healthcare applications.
