import streamlit as st

# Define the pages
main_page = st.Page("home.py", title="Home", icon=":material/home:")
page_chat = st.Page("pages/chat.py", title="Chat with the data", icon=":material/chat:")
page_graph = st.Page("pages/graph.py", title="Interactive Graph", icon=":material/graph_5:")
page_catalog = st.Page("pages/catalog.py", title="Product Catalog (sample)", icon=":material/store:")
page_stats = st.Page("pages/stats.py", title="Graph Statistics", icon=":material/analytics:")
page_purpose = st.Page("pages/purpose.py", title="Tool Purpose", icon=":material/info:", visibility="hidden")
page_license = st.Page("pages/license.py", title="License", icon=":material/license:", visibility="hidden")

# Set up navigation
pg = st.navigation([main_page, 
                    page_chat, 
                    page_graph,
                    page_catalog,
                    page_stats,
                    page_purpose,
                    page_license],
                    position="sidebar",)

# Run the selected page
pg.run()



with st.container(key="site-credit"):
    st.caption(
        "Built with :material/emoji_food_beverage: by "
        "[Marwa Maghnie](https://www.linkedin.com/in/marwa-maghnie/) &nbsp;|&nbsp; "
        "<a href='purpose' target='_self'>Why?</a><br>"
        "<a href='license' target='_self'>© 2026 All rights reserved.</a><br>",
        unsafe_allow_html=True
    )

st.html(
    """
    <style>
    .st-key-site-credit {
        position: fixed;
        top: 3.4rem;
        right: 2rem;
        z-index: 100;
        max-width: 310px;
        text-align: right;
        pointer-events: none;
        background-color: rgba(251, 248, 241, 0.85);
        backdrop-filter: blur(4px);
        border-radius: 8px;
        padding: 1rem 0.7rem;
        box-shadow: 0 1px 4px rgba(74, 63, 53, 0.1);
    }
    .st-key-site-credit * {
        pointer-events: auto;
    }
    .st-key-site-credit p {
        font-size: 0.92rem;
        line-height: 1.5;
        margin: 0;
        color: rgba(74, 63, 53, 0.55);
    }
    .st-key-site-credit a {
        color: rgba(74, 63, 53, 0.65);
        text-decoration: none;
    }
    .st-key-site-credit a:hover {
        color: rgba(74, 63, 53, 0.9);
        text-decoration: underline;
    }
    </style>
    """
)


    