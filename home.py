"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

import os
from typing import List, Dict

import streamlit as st

from utils.util import load_company_config, get_neo4j_driver

st.markdown("""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
""", unsafe_allow_html=True)
    
# --- Streamlit App ---
def main() -> None:
    """Main application entry point."""

    company_config = load_company_config(os.getenv("COMPANY", "libanjus"))
    st.set_page_config(
        page_title=f"{company_config['display_name']} KG Assistant",
        page_icon= company_config.get("icon", ":material/home:"),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    company_color = company_config.get("color", "#2E8B57")
    st.markdown(f"""
    <style>
        .stApp {{ background-color: #F0F8F0; }}
        .stChatMessage {{ padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; background-color: #FFFFFF; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stChatMessage p {{ margin: 0; color: {company_color}; }}
        .user-message {{ background-color: #E8F5E8 !important; margin-left: 20%; border-left: 3px solid {company_color}; }}
        .assistant-message {{ background-color: #FFFFFF !important; margin-right: 20%; border-left: 3px solid {company_color}; }}
        .stButton>button {{ background-color: {company_color} !important; color: white !important; border: none !important; }}
        .stButton>button:hover {{ background-color: {company_color}CC !important; }}
        .stSidebar {{ background-color: #FFFFFF !important; }}
        h1, h2, h3 {{ color: {company_color} !important; }}
        .stExpander {{ border: 1px solid {company_color} !important; border-radius: 0.5rem !important; }}
    </style>
    """, unsafe_allow_html=True)

    st.title(f"{company_config['icon']} {company_config['display_name']} AI Assistant")
    # st.markdown(f"*{company_config['description']}*")

    st.markdown("""
    ### **AI-Powered Business Insights for Lebanese Retail**
    *Answer complex customer and operational questions in plain English using your existing data.*

    **For Customers:** *"Where can I find gluten-free desserts near Hamra open after 6pm?"*  
    **For Executives:** *"Which retailers cover the most products in Beirut?"*
    """)

    with st.expander(":material/search_insights: How This Helps Your Business - **Just a few of the possibilities**", expanded=True):
        st.markdown("""
        | **Use Case**               | **Business Impact**                          |
        |----------------------------|---------------------------------------------|
        | *Customer dietary questions* | Improve accessibility & loyalty for niche markets (celiac, vegan, etc.) |
        | *Real-time store/product queries* | Reduce support calls, empower in-store staff |
        | *Distribution optimization* | Identify gaps, reduce logistics costs       |
        | *Competitive intelligence*   | Spot trends in product availability & pricing|
        """)

    # CTA
    if st.button("Try it out: Chat with the AI", 
                 icon=":material/start:", type="tertiary", width="stretch"):
        st.switch_page("pages/chat.py")

    st.markdown("### **Why Knowledge Graphs + LLMs?**")
    benefits = [
        ("fact_check", "Accuracy", 
         "Answers are grounded in your data (reduced hallucinations)"),
        ("conversation", "Conversational", 
         "Ask in natural language and get plain-English answers"),
        ("insights", "Insights", 
         "Connect the dots between product data and customer wishes"),
        ("psychology", "Context", "Consider the why behind questions (dietary restrictions, moods, etc.)"),

        ("emoji_objects", "Explainability", "For developers: See the generated Cypher query and trace how answers are derived"),      
        ("speed", "Speed", "Reduce deployment time (uses your existing databases)"),
        ("upgrade", "Future-Proof", "Easily add new data (products, stores, distributors) without lengthy re-training"),
        ("diversity_1", "Local Impact", "Uses local context to give community-specific answers"),
    ]
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(benefits):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background: #F8F9FA;
                        padding: 1.25rem;
                        border-radius: 0.75rem;
                        border-left: 4px solid {company_color};
                        margin-bottom: 1rem;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        min-height: 140px;">
                <span class="material-symbols-outlined" style="font-size: 1.75rem; color: {company_color}; margin-bottom: 0.5rem; display: block; text-align: center;">{icon}</span>
                <div style="font-weight: 600; margin-bottom: 0.5rem; color: #333; text-align: center;">{title}</div>
                <div style="font-size: 0.85rem; color: #555; line-height: 1.4; text-align: center;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

    with st.expander(":material/build: **Under the Hood: How It Works**", expanded=False):
        st.image("static/kg_llm_app_architecture_icons.svg", 
                 width="stretch",
                 caption=":material/counter_1: Potential shoppers ask their questions " \
                 "using everyday language within the app (Streamlit). " \
                 "In the background, a large language model (Google Gemini in this case) " \
                 "converts the free-text question into a structured query (Cypher). " \
                 "The query is then executed against a knowledge graph hosted in the cloud (Neo4j AuraDB). " \
                 "The knowledge graph contains product information as linked entities, allowing " \
                 "questions that need rich context to be answered effectively." \
                 "The response to the query is returned in the form of data points, which is then " \
                 "converted to natural language with the help of the LLM and displayed to the " \
                 "user." )


    # Test connection upfront
    try:
        driver = get_neo4j_driver()
        with driver.session() as s:
            count = s.run("MATCH (p:Product) RETURN count(p)").single()[0]
        print("Connected to Neo4j database.")
    except Exception as e:
        st.warning(f":material/globe_2_question: Connection failed: {str(e)}. Trying refreshing the page.")
        st.stop()
       

if __name__ == "__main__":
    main()