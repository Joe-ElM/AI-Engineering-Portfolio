# Interview Practice App

Practice personalized interview questions with AI using prompt engineering and OpenAI.

---

## Description

This is a fully functional **Interview Preparation App** developed using **Streamlit** and **OpenAI's GPT-4o API**. The app generates personalized interview questions based on your topic or role input. It supports advanced prompt engineering techniques and customization, making it ideal for job seekers looking to simulate real interview scenarios.

---

## Features Implemented

### Core Requirements

- [x] Single-page app built using Streamlit
- [x] OpenAI API integration
- [x] Modular project structure (with `main.py`, `openai_client.py`, `prompts.py`, etc.)
- [x] Three different system prompts (Zero-shot, Few-shot, Chain-of-Thought)
- [x] Customizable temperature setting via slider
- [x] Input validation using `guards.py`

### Prompt Engineering Techniques

- [x] Zero-shot prompting
- [x] Few-shot prompting (with examples)
- [x] Chain-of-thought prompting (step-by-step reasoning)

### Security

- [x] Input validation (guards against empty or meaningless input)
- [x] API key hidden via Streamlit Secrets (no hardcoded credentials)

### Customization Options (Sidebar)

- [x] Prompt style selection
- [x] Difficulty level (Easy / Medium / Hard)
- [x] Response detail level (Concise / Detailed)
- [x] Temperature slider (0.0 to 1.0, step 0.2)
- [x] Number of questions (1–5)
- [x] Dynamic `max_tokens` calculation based on question count and prompt style

### Deployment

- [x] Deployed to **Streamlit Cloud**

---

## Optional Tasks Completed

### Easy Level

- [x] Simulate different difficulty levels (Easy, Medium, Hard)
- [x] Concise vs. detailed response styles
- [x] Improve prompts for specific domains (data analyst / scientist)

### Medium Level

- [x] Dynamically bind `max_tokens` to number of questions
- [x] Add slider controls for OpenAI temperature
- [x] Deployed app on Streamlit Cloud

### Ignored Tasks / Not Planned

- [ ] Add RAG support for job description-based prep
- [ ] Add multiple LLM support
- [ ] Add price estimation per prompt
- [ ] Critique feedback generation
- [ ] Jailbreak detection tests

---

## Project Structure

```text
📦 interview-practice-app
├── main.py                # Main Streamlit app
├── main_sp1.py           # Backup of Sprint 1 structure
├── prompts.py            # Prompt templates (zero-shot, few-shot, CoT)
├── openai_client.py      # OpenAI API client wrapper
├── guards.py             # Input validation
├── utils.py              # Utility functions (e.g., token scaling)
├── requirements.txt      # Dependencies
├── .gitignore            # Ignore .env and other local files
```

---

## Example Use Case

1. Enter your topic: `Data Scientist`
2. Choose prompt style: `Few-shot`
3. Choose difficulty: `Medium`
4. Set number of questions: `3`
5. Choose: `Detailed`
6. Generate personalized practice interview questions with high-quality AI answers.

---

## Installation (Optional for Local Use)

```bash
pip install -r requirements.txt
streamlit run main.py
```

---

## Credits

Created as part of the **AI Engineering Sprint 1** project on **Turing College**.

---

## 📍Status

**Working and Deployed**

🔗 [Live App on Streamlit](https://data-interview-app.streamlit.app/)
