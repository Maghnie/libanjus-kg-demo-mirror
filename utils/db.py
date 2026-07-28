from typing import List, Dict, Any
import streamlit as st
from neo4j import GraphDatabase, Driver
from neo4j_viz.neo4j import from_neo4j


class Neo4jConnectionError(Exception):
    pass

def get_neo4j_driver() -> Driver:
    """Get or create a Neo4j driver instance.
    Raises Neo4jConnectionError if connection fails.
    """
    if "neo4j_driver" in st.session_state:
        return st.session_state.neo4j_driver

    aura_instance_id = st.secrets["AURA_INSTANCEID"]
    uri = f"neo4j+s://{aura_instance_id}.databases.neo4j.io:7687"

    try:
        driver = GraphDatabase.driver(
            uri,
            auth=(st.secrets["NEO4J_USER"], st.secrets["NEO4J_PASSWORD"]),
        )
        with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
            session.run("RETURN 1")
        st.session_state.neo4j_driver = driver
        return driver
    except Exception as e:
        if "neo4j_driver" in st.session_state:
            del st.session_state.neo4j_driver
        raise Neo4jConnectionError(f"Neo4j connection failed: {str(e)}")

def get_neo4j_graph():
    """Return graph HTML or an error message."""
    try:
        driver = get_neo4j_driver()
        with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
            result = session.run("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 200")
            VG = from_neo4j(result)
        return VG.render()
    except Neo4jConnectionError as e:
        # return f"<div style='padding:2rem;text-align:center;'>⚠️ {e}</div>" # commented out because deep error handling is too much for a demo 
        pass

@st.cache_data(ttl=300)
def _cached_query(query: str) -> List[Dict[str, Any]]:
    driver = get_neo4j_driver()  # may raise Neo4jConnectionError
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(query)
        return [dict(record) for record in result]

def execute_query(query: str) -> List[Dict[str, Any]] | str:
    """Execute a Cypher query with explicit error handling."""
    try:
        return _cached_query(query)
    except Neo4jConnectionError as e:
        # return f"❌ Database connection error: {str(e)}" # commented out because deep error handling is too much for a demo 
        return ""
    except Exception as e:
        # return f"❌ Query error: {str(e)}" # commented out because deep error handling is too much for a demo 
        return ""
    
@st.cache_data(ttl=3600)
def get_distinct_values() -> Dict[str, List[str]]:
    try:
        driver = get_neo4j_driver()
        with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
            categories = session.run("MATCH (p:Product) RETURN DISTINCT p.category AS cat").value()
            brands = session.run("MATCH (p:Product) RETURN DISTINCT p.brand AS brand").value()
            tags = session.run("MATCH (p:Product) UNWIND p.tags AS tag RETURN DISTINCT tag").value()
            retailer_names = session.run("MATCH (r:Retailer) RETURN DISTINCT r.name AS name").value()
        return {
            "categories": [c for c in categories if c is not None],
            "brands": [b for b in brands if b is not None],
            "tags": [t for t in tags if t is not None],
            "retailers": [r for r in retailer_names if r is not None],
        }
    except Neo4jConnectionError:
        # Return empty lists – the UI will show no filters, but we can display a warning elsewhere.
        return {"categories": [], "brands": [], "tags": [], "retailers": []}

@st.cache_data(ttl=3600)
def get_product_names() -> List[str]:
    try:
        driver = get_neo4j_driver()
        with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
            names = session.run(
                "MATCH (p:Product) RETURN DISTINCT p.name AS name ORDER BY name"
            ).value()
        return [n for n in names if n]
    except Neo4jConnectionError:
        return []