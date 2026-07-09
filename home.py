"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

import os
from typing import List, Dict

import streamlit as st

from utils.util import load_company_config, get_neo4j_driver
    
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

    st.title(f"{company_config['icon']} {company_config['display_name']} Knowledge Graph Assistant")
    st.markdown(f"*{company_config['description']}*")

    # Test connection upfront
    try:
        driver = get_neo4j_driver()
        with driver.session() as s:
            count = s.run("MATCH (p:Product) RETURN count(p)").single()[0]
        st.bottom.success(f"Connected to Neo4j database.", icon="✅")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}. Trying refreshing the page.")
        st.stop()
       

if __name__ == "__main__":
    main()