import streamlit as st

from utils.catalog import get_product_catalog


st.set_page_config(page_title="KG Assistant - Product Catalog", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header("🧾 Product Catalog - A sample")

st.sidebar.markdown("""
<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#EA3323"><path d="M516.27-262.49q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8ZM298.85-355.38v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-18.46q0-26.85 17.62-44.19Q334.1-820 358.85-820h240q24.75 0 42.37 17.35 17.62 17.34 17.62 44.19V-740h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.3-27.96 77.03-27.96 33.73-72.81 45.42V-200q0 24.75-17.62 42.37Q623.6-140 598.85-140h-240q-24.75 0-42.38-17.63-17.62-17.62-17.62-42.37v-32.93q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.03h98.46Zm60 155.38h240v-560h-240v560Zm0 0v-560 560Z"/></svg> 
**Note: This is a demo application.** The AI assistant is trained on a **sample** dataset 
of the LibanJus product line and retailers. It does not have complete or up-to-date information. 
Please verify any critical information with official sources.
""",
unsafe_allow_html=True)

# LOAD CATALOG BEFORE SIDEBAR RENDERS to prevent race condition
catalog = get_product_catalog()
      
if not catalog:
    st.warning("⚠️ No products found. Did you run `python load_kg_data.py`?")
else:
    for category, products in catalog.items():
        with st.expander(f"📦 {category}"):
            for product in products:
                tags = ", ".join(product["tags"]) if product["tags"] else "No tags"
                st.markdown(f"**{product['name']}**  \n*Tags: {tags}*")

st.divider()
if st.button("🔄 Reset Connection", width='stretch'):
    if "neo4j_driver" in st.session_state:
        del st.session_state.neo4j_driver
    st.cache_data.clear()
    st.rerun()