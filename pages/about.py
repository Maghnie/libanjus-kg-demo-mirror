"""About page – explains the tool and architecture."""

from __future__ import annotations

import streamlit as st


# Use the already-loaded config from app.py
config = st.session_state.get("company_config")
if not config:
    st.error("Company config not loaded. Please return to the main page.")
    st.stop()

display_name = config["display_name"]

# --- Page content -----------------------------------------------------------
# Kept as plain data so the copy can be edited without touching any styling
# or layout code below.

USE_CASES_TABLE = """
| **Use Case**               | **Business Impact**                          |
|----------------------------|---------------------------------------------|
| *Distribution optimization* | Identify gaps, reduce logistics costs       |
| *Competitive intelligence*   | Spot trends in product availability & pricing|
| *Customer dietary questions* | Improve accessibility & loyalty for niche markets (celiac, vegan, etc.) |
| *Real-time store/product queries* | Reduce support calls, empower in-store staff |
"""

BENEFITS = [
    ("fact_check", "Accuracy",
     "Answers are grounded in your data (reduced hallucinations)"),
    ("conversation", "Conversational",
     "Ask in natural language and get plain-English answers"),
    ("insights", "Insights",
     "Connect the dots between product data and customer wishes"),
    ("psychology", "Context",
     "Consider the why behind questions (dietary restrictions, moods, etc.)"),
    ("emoji_objects", "Explainability",
     "For developers: See the generated Cypher query and trace how answers are derived"),
    ("speed", "Speed",
     "Reduce deployment time (uses your existing databases)"),
    ("upgrade", "Future-Proof",
     "Easily add new data (products, stores, distributors) without lengthy re-training"),
    ("diversity_1", "Local Impact",
     "Uses local context to give community-specific answers"),
]

ARCHITECTURE_CAPTION = (
    ":material/counter_1: Potential shoppers ask their questions "
    "using everyday language within the app (Streamlit)."
    ":material/counter_2: In the background, a large language model (Google Gemini in this case) "
    "converts the free-text question into a structured query (Cypher). "
    ":material/counter_3: The query is then executed against a knowledge graph hosted in the cloud (Neo4j AuraDB). "
    "The knowledge graph contains product information as linked entities, allowing "
    "questions that need rich context to be answered effectively."
    ":material/counter_4: The response to the query is returned in the form of data points. "
    ":material/counter_5: The raw response is then "
    "converted to natural language with the help of the LLM and :material/counter_6: displayed to the "
    "user."
)


# --- Section renderers --------------------------------------------------

def render_hero() -> None:
    st.markdown(
        f"""
        <div class="hero-banner">
            <h1> About the AI Product Discovery Assistant</h1>
            <p class="hero-tagline"><strong>
            Why this matters and how it works</strong></p>
            <p class="hero-subtext">
                Answer complex operations and customer questions in plain English using your existing data.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_demo() -> None:
    st.video('static/demo.mp4', start_time='7s', end_time='38s', loop=True, autoplay=True)

def render_use_cases() -> None:
    with st.expander(
        ":material/search_insights: How This Helps Your Business - **Just a few of the possibilities**",
        expanded=True,
    ):
        st.markdown(USE_CASES_TABLE)


def render_cta() -> None:
    if st.button(
        "Try it out: Chat with the AI",
        icon=":material/start:",
        type="tertiary",
        width="stretch",
    ):
        st.switch_page("pages/chat.py")


def render_benefits_grid() -> None:
    st.markdown("### :color[**Why Knowledge Graphs + LLMs?**]{background='white'}")
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(BENEFITS):
        with cols[i % 4]:
            st.markdown(
                f"""
                <div class="benefit-card">
                    <span class="material-symbols-outlined benefit-icon">{icon}</span>
                    <div class="benefit-title">{title}</div>
                    <div class="benefit-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_architecture_section() -> None:
    with st.expander(":material/build: **Under the Hood: How It Works**", expanded=True):
        st.image(
            "static/kg_llm_app_architecture_icons.svg",
            width="stretch",
        )
        st.markdown(ARCHITECTURE_CAPTION)


# --- Entry point ---------------------------------------------------------

def main() -> None:
    
    render_hero()
    render_demo()
    render_use_cases()
    render_cta()
    render_benefits_grid()
    render_architecture_section()


if __name__ == "__main__":
    main()
