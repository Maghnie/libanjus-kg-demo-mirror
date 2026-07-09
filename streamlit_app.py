import streamlit as st

# Define the pages
main_page = st.Page("home.py", title="Home", icon=":material/home:")
page_chat = st.Page("pages/chat.py", title="Chat with the data", icon=":material/chat:")
page_graph = st.Page("pages/graph.py", title="Interactive Graph", icon=":material/graph_5:")
page_catalog = st.Page("pages/catalog.py", title="Product Catalog (sample)", icon=":material/store:")
page_stats = st.Page("pages/stats.py", title="Graph Statistics", icon=":material/analytics:")
page_purpose = st.Page("pages/purpose.py", title="Tool Purpose", icon=":material/info:", visibility="hidden")

# Set up navigation
pg = st.navigation([main_page, 
                    page_chat, 
                    page_graph,
                    page_catalog,
                    page_stats,
                    page_purpose],
                    position="sidebar",)

# Run the selected page
pg.run()

st.bottom.markdown("© 2026 All rights reserved. | " \
"Built with :material/emoji_food_beverage: by [Marwa Maghnie](https://www.linkedin.com/in/marwa-maghnie/) [(Why?)](purpose)")



    