import streamlit as st

from utils.graph import get_graph_legend_html, get_pyvis_graph
from utils.db import get_product_names
from utils.error_handling import render_503_error


# Load the global config
config = st.session_state.get("company_config")
if not config:
    st.error("Company config not found. Please go back to the main page.")
    st.stop()

display_name = config["display_name"]
company_icon = config["icon"]

st.header(f"{company_icon} {display_name} Interactive Knowledge Graph",
          text_alignment="center",
          divider="gray")


st.caption("""
:material/experiment: :grey-background[**This is an experimental, unofficial, and unaffiliated demo application. The AI assistant is trained on a **sample** dataset 
of the product line and retailers, as well as artificially generated data. It does not have 
complete or up-to-date information. Please verify any critical information with official sources.**]
""")

col_controls, col_graph = st.columns([1, 3])

with col_controls:
    st.markdown("**Focus**")
    product_names = get_product_names()
    show_all = st.checkbox("Show full graph", value=False)
    center_node = None
    if not show_all and product_names:
        center_node = st.selectbox("Product", product_names, index=0)
    depth = st.slider(
        "Hops from focus product",
        min_value=1, max_value=4, value=2,
        help="How many relationship hops out from the product to include.",
        disabled=show_all,
    )
    limit = st.slider(
        "Max relationships",
        min_value=25, max_value=200, value=100, step=25,
        help="Caps how many edges are pulled, to keep the graph legible.",
    )
    st.caption("Layout is static — drag a node to reposition it")

with col_graph:
    st.markdown(get_graph_legend_html(), unsafe_allow_html=True)
    connection_successful = True
    with st.spinner("Building graph..."):
        try:
            html = get_pyvis_graph(
                limit=limit,
                center_node=center_node,
                depth=depth,
            )
            if html and len(html) > 100:
                st.iframe(html, height=650)
            else:
                st.warning("No graph data to display for this selection.")
        except Exception as e:
            # --- commented out because deep error handling is too much for a demo ---
            # st.error(f"Failed to render graph")
            # import traceback
            # st.code(traceback.format_exc())
            # ---
            connection_successful = False

    if not connection_successful:
        render_503_error()
        st.stop()
