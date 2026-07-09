import streamlit as st

from utils.util import get_product_catalog


st.set_page_config(page_title="KG Assistant - Product Catalog", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header("🧾 Product Catalog")

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