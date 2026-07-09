import streamlit as st

from utils.util import get_graph_statistics


st.set_page_config(page_title="KG Assistant - Statistics", 
                   page_icon=":material/nutrition:",
                   layout="wide")

st.header("📊 Knowledge Graph Statistics")

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
col1.metric("🍎 Products", stats["product_count"])
col2.metric("🏪 Retailers", stats["retailer_count"])
col3.metric("📦 Distributors", stats["distributor_count"])
col4.metric("🏭 Factories", stats["factory_count"])
col5.metric("🔗 Relationships", stats["relationship_count"])

st.divider()

# === Top Performers ===
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏆 Most Available Products")
    for item in stats["top_products"]:
        st.metric(item["product"], f"{item['count']} retailers")

with col2:
    st.subheader("🏪 Retailers with Most Products")
    for item in stats["top_retailers"]:
        st.metric(item["retailer"], f"{item['count']} products")

st.divider()

# === Distributions (Bar Charts) ===
col1, col2 = st.columns(2)
with col1:
    st.subheader("📦 Product Categories")
    if stats["categories"]:
        st.bar_chart(
            {item["category"]: item["count"] for item in stats["categories"]},
            width='stretch'
        )

with col2:
    st.subheader("🏷️ Product Brands")
    if stats["brands"]:
        st.bar_chart(
            {item["brand"]: item["count"] for item in stats["brands"]},
            width='stretch'
        )