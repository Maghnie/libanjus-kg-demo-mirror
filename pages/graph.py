import streamlit as st

from utils.util import get_product_names, get_graph_legend_html, get_pyvis_graph

st.set_page_config(page_title="KG Assistant - Interactive Knowledge Graph", 
                   page_icon=":material/nutrition:")

st.header(":material/graph_5: Interactive Knowledge Graph")

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
    st.caption("Layout is static (no physics) — drag a node to reposition it; it will stay put.")

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