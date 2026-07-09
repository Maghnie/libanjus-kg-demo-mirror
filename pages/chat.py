from typing import List, Dict
import streamlit as st

from utils.util import generate_cypher, execute_query, format_answer


st.set_page_config(page_title="KG Assistant - Chat with the Knowledge Graph", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header("🧙‍♂️💬 Ask the AI about any products")

if "messages" not in st.session_state:
    st.session_state.messages: List[Dict[str, str]] = []

col_sample_qs, col_chat_box = st.columns([0.2,0.8])
        
with col_sample_qs:
    st.markdown("**Try These:**")
    example_questions = [
        "As a celiac, what sweet products can I get?",
        "Where can I get organic Labneh near Al-Hamra?",
        "Which retailers are open at 10 am on a Sunday and have fat-free milk?"
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