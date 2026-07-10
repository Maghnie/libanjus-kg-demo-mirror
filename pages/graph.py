import streamlit as st

from utils.graph import get_graph_legend_html, get_pyvis_graph
from utils.db import get_product_names

st.set_page_config(page_title="KG Assistant - Interactive Knowledge Graph", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header(":material/graph_5: Interactive Knowledge Graph")

st.sidebar.markdown("""
<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="#EA3323"><path d="M516.27-262.49q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8Zm0-180q14.88-14.79 14.88-37.42 0-22.63-14.79-37.51-14.8-14.89-37.42-14.89-22.63 0-37.52 14.8-14.88 14.79-14.88 37.42 0 22.63 14.79 37.51 14.8 14.89 37.43 14.89 22.62 0 37.51-14.8ZM298.85-355.38v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-69.85q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.04h98.46v-18.46q0-26.85 17.62-44.19Q334.1-820 358.85-820h240q24.75 0 42.37 17.35 17.62 17.34 17.62 44.19V-740h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.31-27.96 77.04-27.96 33.73-72.81 45.42v69.85h100.77q0 43.3-27.96 77.03-27.96 33.73-72.81 45.42V-200q0 24.75-17.62 42.37Q623.6-140 598.85-140h-240q-24.75 0-42.38-17.63-17.62-17.62-17.62-42.37v-32.93q-44.85-11.69-71.66-45.42-26.8-33.73-26.8-77.03h98.46Zm60 155.38h240v-560h-240v560Zm0 0v-560 560Z"/></svg> 
**Note: This is a demo application.** The AI assistant is trained on a **sample** dataset 
of the LibanJus product line and retailers. It does not have complete or up-to-date information. 
Please verify any critical information with official sources.
""",
unsafe_allow_html=True)

col_controls, col_graph = st.columns([1, 3])

with col_controls:
    st.markdown("**Focus**")
    product_names = get_product_names()
    show_all = st.checkbox("Show full graph (no focus product)", value=False)
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
            st.error(f"Failed to render graph: {e}")
            import traceback
            st.code(traceback.format_exc())