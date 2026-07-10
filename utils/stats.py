import streamlit as st
from utils.db import get_neo4j_driver


@st.cache_data(ttl=3600)
def get_graph_statistics():
    """Fetch all graph statistics in a single cached call."""
    driver = get_neo4j_driver()
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        # Basic counts
        product_count = session.run("MATCH (p:Product) RETURN count(p)").single()[0]
        retailer_count = session.run("MATCH (r:Retailer) RETURN count(r)").single()[0]
        distributor_count = session.run("MATCH (d:Distributor) RETURN count(d)").single()[0]
        factory_count = session.run("MATCH (f:Factory) RETURN count(f)").single()[0]
        location_count = session.run("MATCH (l:Location) RETURN count(l)").single()[0]
        relationship_count = session.run("MATCH ()-[r]->() RETURN count(r)").single()[0]

        # Top products by availability
        top_products = session.run("""
            MATCH (p:Product)-[:AVAILABLE_AT]->(r:Retailer)
            RETURN p.name AS product, count(r) AS count
            ORDER BY count DESC LIMIT 5
        """).data()

        # Top retailers by product count
        top_retailers = session.run("""
            MATCH (p:Product)-[:AVAILABLE_AT]->(r:Retailer)
            RETURN r.name AS retailer, count(p) AS count
            ORDER BY count DESC LIMIT 5
        """).data()

        # Category distribution
        categories = session.run("""
            MATCH (p:Product)
            RETURN p.category AS category, count(p) AS count
            ORDER BY count DESC
        """).data()

        # Brand distribution
        brands = session.run("""
            MATCH (p:Product)
            RETURN p.brand AS brand, count(p) AS count
            ORDER BY count DESC
        """).data()

        return {
            "product_count": product_count,
            "retailer_count": retailer_count,
            "distributor_count": distributor_count,
            "factory_count": factory_count,
            "location_count": location_count,
            "relationship_count": relationship_count,
            "top_products": top_products,
            "top_retailers": top_retailers,
            "categories": categories,
            "brands": brands,
        }