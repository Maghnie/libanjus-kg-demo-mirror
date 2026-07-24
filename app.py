import streamlit as st
import glob
from pathlib import Path

# -------------------------------------------------------------------
# 0. MUST BE THE FIRST STREAMLIT COMMAND
# -------------------------------------------------------------------
st.set_page_config(
    page_title="AI Shopping Assistant",
    page_icon="static/app_icon.bmp",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.html("""
    <style>
        .stMainBlockContainer {
            max-width: 60rem; /* Change this value to make it wider or narrower */
        }
    </style>
""")

# -------------------------------------------------------------------
# 1. Discover available companies
# -------------------------------------------------------------------
company_files = glob.glob("config/companies/*.json")
company_names = [Path(f).stem for f in company_files]
if not company_names:
    company_names = ["libanjus"]

# -------------------------------------------------------------------
# 2. Read company from URL / session_state
# -------------------------------------------------------------------
params = st.query_params
current = params.get("brand_owner")
if current not in company_names:
    current = company_names[0]
    params["brand_owner"] = current

# Load config and store in session_state for all pages to use
from utils.config import load_company_config
from utils.styles import apply_theme, load_css, load_material_symbols_font

company_config = load_company_config(current)
st.session_state.company_config = company_config
st.session_state.company = current  # keep for backward compatibility

# -------------------------------------------------------------------
# 3. Apply GLOBAL theme, background, fonts, and CSS
# -------------------------------------------------------------------
# Background renderer function (copy from home.py or keep import)
def render_bg(path_bg_light, path_bg_dark, dim_amount=0.75):
    import base64
    theme = st.context.theme.type
    path = Path(path_bg_light)
    if theme == "dark":
        path = Path(path_bg_dark)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    brightness = 255 if theme != "dark" else 0
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba({brightness}, {brightness}, {brightness}, {dim_amount}), 
                                              rgba({brightness}, {brightness}, {brightness}, {dim_amount})),
                               url("data:image/png;base64,{b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

render_bg(
    path_bg_light=company_config["background_image_light"],
    path_bg_dark=company_config["background_image_dark"],
)
load_material_symbols_font()
apply_theme(company_config.get("color", "#2E8B57"))
load_css()

# -------------------------------------------------------------------
# 4. Sidebar company selector (syncs with URL)
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Company Theme")
    selected = st.radio(
        "Select a company",
        company_names,
        index=company_names.index(current),
        key="company_selector",
        label_visibility="collapsed",
    )
    if selected != current:
        params["brand_owner"] = selected
        st.rerun()
    st.divider()

# -------------------------------------------------------------------
# 5. Define pages – CHAT is default
# -------------------------------------------------------------------
page_chat = st.Page("pages/chat.py", title="Chat", icon=":material/chat:", default=True)
page_about = st.Page("pages/about.py", title="About", icon=":material/info:")
page_graph = st.Page("pages/graph.py", title="Interactive Graph", icon=":material/graph_5:")
page_catalog = st.Page("pages/catalog.py", title="Product Catalog", icon=":material/store:")
page_stats = st.Page("pages/stats.py", title="Graph Statistics", icon=":material/analytics:")
page_purpose = st.Page("pages/purpose.py", title="Tool Purpose", icon=":material/info:", visibility="hidden")
page_license = st.Page("pages/license.py", title="License", icon=":material/license:", visibility="hidden")

pg = st.navigation(
    [page_chat, page_about, page_graph, page_catalog, page_stats, page_purpose, page_license],
    position="sidebar",
)
pg.run()

# -------------------------------------------------------------------
# 6. Site credits (unchanged)
# -------------------------------------------------------------------
with st.container(key="site-credit"):
    st.caption(
        "Built with :material/emoji_food_beverage: by "
        "[Marwa Maghnie](https://www.linkedin.com/in/marwa-maghnie/) &nbsp;|&nbsp; "
        "<a href='purpose' target='_self'>Why?</a><br>"
        "<a href='license' target='_self'>© 2026 All rights reserved.</a><br>",
        unsafe_allow_html=True,
    )

# Style 
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
        background-color: rgba(251, 248, 241, 0.7);
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
        color: rgba(74, 63, 53, 0.85);
    }
    .st-key-site-credit a {
        color: rgba(74, 63, 53, 0.85);
        text-decoration: none;
    }
    .st-key-site-credit a:hover {
        color: rgba(74, 63, 53, 0.95);
        text-decoration: underline;
    }
    </style>
    """
)