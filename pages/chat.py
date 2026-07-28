from typing import List, Dict
import streamlit as st

from utils.llm import generate_cypher, format_answer
from utils.db import execute_query
from utils.error_handling import render_503_error


# Load the global config
config = st.session_state.get("company_config")
if not config:
    st.error("Company config not found. Please go back to the main page.")
    st.stop()

display_name = config["display_name"]
company_icon = config["icon"]

st.header(f"{company_icon} Ask the {display_name} AI about any products",
          text_alignment="center",
          divider="gray")


st.caption("""
:material/experiment: :grey-background[**This is an experimental, unofficial, and unaffiliated demo application. The AI assistant is trained on a **sample** dataset 
of the product line and retailers, as well as artificially generated data. It does not have 
complete or up-to-date information. Please verify any critical information with official sources.**]
""")


if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []


col_sample_qs, col_chat_box = st.columns([0.2,0.8])
        
with col_sample_qs:
    st.markdown("**Try These:**")
    example_questions = [
        "As a celiac, what sweet products can I get?",
        "Which retailers are open at 10 am on a Sunday and have fat-free milk?",
        "Where can I get organic Labneh near Al-Hamra?"
    ]
    for q in example_questions:
        if st.button(q, key=f"btn_{hash(q) % 10000}", width='stretch'):
            st.session_state["user_input"] = q
            st.rerun()
    
    st.divider()
    if st.button(":material/delete: Clear Chat", width='stretch'):
        st.session_state.messages = []
        st.rerun()

with col_chat_box:
    st.markdown("**Or start typing:**")
    chat_container = st.container()
    for msg in st.session_state.messages:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question...") or st.session_state.get("user_input"):
        if st.session_state.get("user_input"):
            prompt = st.session_state["user_input"]
            del st.session_state["user_input"]

        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)

        prompt_successful = True
        with st.spinner(":material/psychology: Thinking..."):
            cypher_query = generate_cypher(prompt)
            if not cypher_query:
                st.error("Could not generate a query. Please rephrase.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, I couldn't generate a query. Please try rephrasing.",
                })
                st.rerun()

            results = execute_query(cypher_query)

            if len(results) == 0:   
                prompt_successful = False
            else:          
                answer = format_answer(results, prompt)

                with chat_container.chat_message("assistant"):
                    with st.expander("🔍 See Generated Cypher Query"):
                        st.code(cypher_query, language="cypher")
                    st.markdown(answer)
        
                st.session_state.messages.append({"role": "assistant", "content": answer})

        if not prompt_successful:
            render_503_error()
            st.stop()


            

        