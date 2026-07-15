from typing import List, Dict, Any
import streamlit as st
from neo4j import GraphDatabase, Driver
from neo4j_viz.neo4j import from_neo4j


def get_neo4j_driver() -> Driver:
    """Get or create a Neo4j driver instance (stored in session state)."""
    if "neo4j_driver" not in st.session_state:
        aura_instance_id = st.secrets["AURA_INSTANCEID"]
        uri = f"neo4j+s://{aura_instance_id}.databases.neo4j.io:7687"

        try:
            driver = GraphDatabase.driver(
                uri,
                auth=(st.secrets["NEO4J_USER"], st.secrets["NEO4J_PASSWORD"]),
            )
            # Test connection immediately
            with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
                session.run("RETURN 1")
            st.session_state.neo4j_driver = driver
        except Exception as e:
            st.error(f"🔃 Connection to database paused. Try refreshing the page or contact the page owner.")
            st.stop()  # Stop the app if connection fails

    return st.session_state.neo4j_driver

def get_neo4j_graph():
    driver = get_neo4j_driver()  # reuse your cached driver
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(
            "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 200"  # limit to avoid overload
        )

        VG = from_neo4j(result)  # pass list of dict-like records

    return VG.render()

@st.cache_data(ttl=300)
def _cached_query(query: str) -> List[Dict[str, Any]]:
    # actual cached function that expects a successful result
    driver = get_neo4j_driver()
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(query)
        return [dict(record) for record in result]
    
def execute_query(query: str) -> List[Dict[str, Any]] | str:
    """Execute a Cypher query with explicit error handling."""
    try:
        return _cached_query(query)
    except Exception as e:
        # Clear the driver if it's in a bad state
        if "neo4j_driver" in st.session_state:
            del st.session_state.neo4j_driver
        return f"❌ Query error: {str(e)}"

@st.cache_data(ttl=3600)
def get_distinct_values() -> Dict[str, List[str]]:
    driver = get_neo4j_driver()
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        categories = session.run("MATCH (p:Product) RETURN DISTINCT p.category AS cat").value()
        brands = session.run("MATCH (p:Product) RETURN DISTINCT p.brand AS brand").value()
        # ingredients = session.run("MATCH (p:Product) UNWIND p.ingredients AS ingredient RETURN DISTINCT ingredient").value()
        tags = session.run("MATCH (p:Product) UNWIND p.tags AS tag RETURN DISTINCT tag").value()
        retailer_names = session.run("MATCH (r:Retailer) RETURN DISTINCT r.name AS name").value()
    return {
        "categories": [c for c in categories if c is not None],
        "brands": [b for b in brands if b is not None],
        # "ingredients": [i for i in ingredients if i is not None],
        "tags": [t for t in tags if t is not None],
        "retailers": [r for r in retailer_names if r is not None],
    }

@st.cache_data(ttl=3600)
def get_product_names() -> List[str]:
    """Distinct product names, used to populate the graph-scoping selectbox."""
    driver = get_neo4j_driver()
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        names = session.run(
            "MATCH (p:Product) RETURN DISTINCT p.name AS name ORDER BY name"
        ).value()
    return [n for n in names if n]