from typing import List, Dict
import streamlit as st

from utils.util import generate_cypher, execute_query, format_answer


st.set_page_config(page_title="KG Assistant - Chat with the Knowledge Graph", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header("🧙‍♂️💬 Ask the AI about any products")

st.sidebar.markdown("""
<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#EA3323"><path d="M516.27-262.49q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8ZM298.85-355.38v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-18.46q0-26.85 17.62-44.19Q334.1-820 358.85-820h240q24.75 0 42.37 17.35 17.62 17.34 17.62 44.19V-740h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.3-27.96 77.03-27.96 33.73-72.81 45.42V-200q0 24.75-17.62 42.37Q623.6-140 598.85-140h-240q-24.75 0-42.38-17.63-17.62-17.62-17.62-42.37v-32.93q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.03h98.46Zm60 155.38h240v-560h-240v560Zm0 0v-560 560Z"/></svg> 
**Note: This is a demo application.** The AI assistant is trained on a **sample** dataset 
of the LibanJus product line and retailers. It does not have complete or up-to-date information. 
Please verify any critical information with official sources.
""",
unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []

col_sample_qs, col_chat_box = st.columns([0.2,0.8])
        
with col_sample_qs:
    st.markdown("**Try These:**")
    example_questions = [
        "As a celiac, what sweet products can I get?",
        "Where can I get organic Labneh near Al-Hamra?",
        "Which retailers are open at 10 am on a Sunday and have fat-free milk?",
        "Which retailers cover the most products in Beirut?"
    ]
    for q in example_questions:
        if st.button(q, key=f"btn_{hash(q) % 10000}", width='stretch'):
            st.session_state["user_input"] = q
            st.rerun()
    
    st.divider()
    if st.button("🗑️ Clear Chat", width='stretch'):
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

        with st.spinner("🤔 Thinking..."):
            cypher_query = generate_cypher(prompt)
            if not cypher_query:
                st.error("Could not generate a query. Please rephrase.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, I couldn't generate a query. Please try rephrasing.",
                })
                st.rerun()

            results = execute_query(cypher_query)
            print(results)
            answer = format_answer(results, prompt)

        with chat_container.chat_message("assistant"):
            with st.expander("🔍 See Generated Cypher Query"):
                st.code(cypher_query, language="cypher")
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})