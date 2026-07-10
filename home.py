"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

import base64
import os
from turtle import color

import streamlit as st

from utils.util import load_company_config, get_neo4j_driver
from utils.styles import apply_theme, load_css, load_material_symbols_font

# --- Page content -----------------------------------------------------------
# Kept as plain data so the copy can be edited without touching any styling
# or layout code below.

USE_CASES_TABLE = """
| **Use Case**               | **Business Impact**                          |
|----------------------------|---------------------------------------------|
| *Customer dietary questions* | Improve accessibility & loyalty for niche markets (celiac, vegan, etc.) |
| *Real-time store/product queries* | Reduce support calls, empower in-store staff |
| *Distribution optimization* | Identify gaps, reduce logistics costs       |
| *Competitive intelligence*   | Spot trends in product availability & pricing|
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
    "using everyday language within the app (Streamlit). "
    "In the background, a large language model (Google Gemini in this case) "
    "converts the free-text question into a structured query (Cypher). "
    "The query is then executed against a knowledge graph hosted in the cloud (Neo4j AuraDB). "
    "The knowledge graph contains product information as linked entities, allowing "
    "questions that need rich context to be answered effectively."
    "The response to the query is returned in the form of data points, which is then "
    "converted to natural language with the help of the LLM and displayed to the "
    "user."
)


# --- Section renderers --------------------------------------------------

def render_bg() -> None:
    with open("static/bg_image_home.png", "rb") as f:
        image_object = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{image_object}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }},
    .stMarkdown {{
        background-color: rgba(251, 248, 241, 0.5);
        backdrop-filter: blur(6px);
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 6px rgba(74, 63, 53, 0.08);
    }}
    </style>
    """, unsafe_allow_html=True)

def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-banner">
            <h1>🍊 LibanJus AI Assistant</h1>
            <p class="hero-tagline"><strong>AI-Powered Business Insights for Lebanese Retail</strong></p>
            <p class="hero-subtext">
                Answer complex customer questions in plain English using your existing data.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    with st.expander(":material/build: **Under the Hood: How It Works**", expanded=False):
        st.image(
            "static/kg_llm_app_architecture_icons.svg",
            width="stretch",
            caption=ARCHITECTURE_CAPTION,
        )


def verify_database_connection() -> None:
    """Fail fast (with a friendly message) if Neo4j isn't reachable."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            session.run("MATCH (p:Product) RETURN count(p)").single()
        print("Connected to Neo4j database.")
    except Exception as exc:
        st.warning(f":material/globe_2_question: Connection failed: {exc}. Trying refreshing the page.")
        st.stop()


# --- Entry point ---------------------------------------------------------

def main() -> None:
    """Main application entry point."""
    company_config = load_company_config(os.getenv("COMPANY", "libanjus"))

    st.set_page_config(
        page_title=f"{company_config['display_name']} KG Assistant",
        page_icon=company_config.get("icon", ":material/home:"),
        layout="centered",
        initial_sidebar_state="expanded",
    )

    load_material_symbols_font()
    apply_theme(company_config.get("color", "#2E8B57"))
    load_css()
    
    render_hero()
    render_use_cases()
    render_cta()
    render_benefits_grid()
    render_architecture_section()
    render_bg()

    verify_database_connection()


if __name__ == "__main__":
    main()
