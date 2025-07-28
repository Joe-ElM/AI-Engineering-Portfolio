"""Streamlit-based Interview Practice App using OpenAI GPT models."""


import streamlit     as st
from   openai_client import get_completion
import prompts              # prompt style logic
import guards               # input validation

st.set_page_config(page_title="Interview Practice App", layout="centered")

# --- Header ---
st.title("Interview Practice App")
st.subheader("Practice interview questions with AI")

user_input = st.text_area("Enter your topic, question, or job role:")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Customize AI Behavior")
    prompt_style = st.selectbox("Select Prompt Style", ["Zero-shot", "Few-shot", "Chain-of-thought"])
    difficulty     = st.selectbox("Select Difficulty Level", ["Easy", "Medium", "Hard"])
    response_style = st.selectbox("Response Detail Level", ["Concise", "Detailed"])
    temperature    = st.slider("Creativity (Temperature)", 0.0, 1.0, 0.5, step=0.1)
    num_questions  = st.slider("Number of Questions", 1, 5, 1)

# --- Token Budget ---
scaling_factor = {
                "Zero-shot"       : 1.0,
                "Few-shot"        : 1.25,
                "Chain-of-thought": 1.5
}.get(prompt_style, 1.0)

max_tokens = int(num_questions * 200 * scaling_factor)


# --- Prompt Strategy Mapping ---
prompt_map = {
    "Zero-shot"       : prompts.get_zero_shot_prompt,
    "Few-shot"        : prompts.get_few_shot_prompt,
    "Chain-of-thought": prompts.get_chain_of_thought_prompt,
}

# --- Main Logic ---
if st.button("Generate Interview Question"):

    if not guards.validate_input(user_input):
        st.warning("Invalid input. Please enter something meaningful.")
        st.stop()


    try:
        system_prompt = prompt_map.get(prompt_style, lambda: "You are an interview coach.")()
        system_prompt += (
            f"Generate {num_questions} {difficulty.lower()} interview question(s). "
            f"Each question should be followed by a {response_style.lower()} answer. "
            "Separate them clearly."
)


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user"  , "content": user_input}
        ]

        response = get_completion(
                                messages    = messages,
                                temperature = temperature,
                                model       = "gpt-4o-mini",
                                max_tokens  = max_tokens
                               )

        st.markdown("### AI-Generated Interview Response")
        st.write(response)

    except Exception as e:
        st.error("Oops! Something went wrong while generating the response.")
        st.code(str(e))
