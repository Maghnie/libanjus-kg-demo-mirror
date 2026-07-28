import streamlit as st

from utils.catalog import get_product_catalog
from utils.error_handling import render_503_error


# Load the global config
config = st.session_state.get("company_config")
if not config:
    st.error("Company config not found. Please go back to the main page.")
    st.stop()

display_name = config["display_name"]
company_icon = config["icon"]

st.header(f"{company_icon} {display_name} Product Catalog - A sample",
          text_alignment="center",
          divider="gray")


st.caption("""
:material/experiment: :grey-background[**This is an experimental, unofficial, and unaffiliated demo application. The AI assistant is trained on a **sample** dataset 
of the product line and retailers, as well as artificially generated data. It does not have 
complete or up-to-date information. Please verify any critical information with official sources.**]
""")

# LOAD CATALOG BEFORE SIDEBAR RENDERS to prevent race condition
catalog = get_product_catalog()
      
if not catalog:
    render_503_error()
    st.stop()
else:
    for category, products in catalog.items():
        with st.expander(f":material/package_2: {category}"):
            for product in products:
                tags = ", ".join(product["tags"]) if product["tags"] else "No tags"
                st.markdown(f"**{product['name']}**  \n*Tags: {tags}*")

st.divider()
if st.button(":material/refresh: Reset Connection", width='stretch'):
    if "neo4j_driver" in st.session_state:
        del st.session_state.neo4j_driver
    st.cache_data.clear()
    st.rerun()