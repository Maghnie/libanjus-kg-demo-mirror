import streamlit as st

from utils.stats import get_graph_statistics


# Load the global config
config = st.session_state.get("company_config")
if not config:
    st.error("Company config not found. Please go back to the main page.")
    st.stop()

display_name = config["display_name"]
company_icon = config["icon"]

st.header(f"{company_icon} {display_name} Knowledge Graph Statistics",
          text_alignment="center",
          divider="gray")


st.caption("""
:material/experiment: :grey-background[**This is an experimental, unofficial, and unaffiliated demo application. The AI assistant is trained on a **sample** dataset 
of the product line and retailers, as well as artificially generated data. It does not have 
complete or up-to-date information. Please verify any critical information with official sources.**]
""")


# Custom styling for metrics
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: bold;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #30A9FA;
    }
</style>
""", unsafe_allow_html=True)

stats = get_graph_statistics()

# === Key Metrics Row ===
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(":material/inventory: Products", stats["product_count"])
col2.metric(":material/storefront: Retailers", stats["retailer_count"])
col3.metric(":material/warehouse: Distributors", stats["distributor_count"])
col4.metric(":material/factory: Factories", stats["factory_count"])
col5.metric(":material/link: Relationships", stats["relationship_count"])

st.divider()

# === Top Performers ===
col1, col2 = st.columns(2)
with col1:
    st.subheader(":material/trophy: Most Available Products")
    for item in stats["top_products"]:
        st.metric(item["product"], f"{item['count']} retailers")

with col2:
    st.subheader(":material/storefront: Retailers with Most Products")
    for item in stats["top_retailers"]:
        st.metric(item["retailer"], f"{item['count']} products")

st.divider()

# === Distributions (Bar Charts) ===
col1, col2 = st.columns(2)
with col1:
    st.subheader(":material/category: Product Categories")
    if stats["categories"]:
        st.bar_chart(
            {item["category"]: item["count"] for item in stats["categories"]},
            width='stretch'
        )

with col2:
    st.subheader(":material/label: Product Brands")
    if stats["brands"]:
        st.bar_chart(
            {item["brand"]: item["count"] for item in stats["brands"]},
            width='stretch'
        )