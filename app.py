"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import requests
import streamlit as st
from neo4j import GraphDatabase, Driver

# --- Constants ---
SCHEMA = """
Nodes:
- Product (name, description, ingredients, tags, category)
- Retailer (name, location)
- Location (address, city, neighborhood, lat, lon)
- TimeSlot (day, start, end)
- Factory (name, location)
- Distributor (name, location)

Relationships:
- (Product)-[:AVAILABLE_AT]->(Retailer)
- (Product)-[:MANUFACTURED_AT]->(Factory)
- (Product)-[:DISTRIBUTED_BY]->(Distributor)
- (Distributor)-[:SUPPLIES_TO]->(Retailer)
- (Retailer)-[:LOCATED_AT]->(Location)
- (Retailer)-[:OPEN_AT]->(TimeSlot)
"""

# --- Helper Functions ---
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
            st.error(f"❌ Neo4j connection failed: {str(e)}")
            st.error("Check your AURA_INSTANCEID, NEO4J_USER, and NEO4J_PASSWORD in .streamlit/secrets.toml")
            st.stop()  # Stop the app if connection fails

    return st.session_state.neo4j_driver

@st.cache_data(ttl=300)  # Cache query results, not the driver
def execute_query(query: str) -> List[Dict[str, Any]] | str:
    """Execute a Cypher query with explicit error handling."""
    try:
        driver = get_neo4j_driver()
        with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
            result = session.run(query)
            return [dict(record) for record in result]
    except Exception as e:
        # Clear the driver if it's in a bad state
        if "neo4j_driver" in st.session_state:
            del st.session_state.neo4j_driver
        return f"❌ Query error: {str(e)}"

def validate_cypher(query: str) -> bool:
    """Validate Cypher query syntax."""
    if not query:
        return False
    query_lower = query.lower().strip()
    return query_lower.startswith(("match", "create", "return"))

def generate_cypher(user_question: str) -> Optional[str]:
    """Generate Cypher query using Mistral AI."""
    api_key = st.secrets.get("MISTRAL_API_KEY")
    if not api_key:
        st.error("Mistral API key not configured")
        return None

    prompt = f"""
    You are an expert Cypher query generator for a Neo4j graph with this schema:
    {SCHEMA}
    Generate a Cypher query to answer: "{user_question}"
    Return ONLY the query (no explanation, no markdown, no backticks).
    """

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistral-tiny",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        query = response.json()["choices"][0]["message"]["content"].strip()

        if "```" in query:
            query = query.split("```")[1].split("```")[0].strip()
        if query.startswith(("cypher", "Cypher")):
            query = query.split("\n")[1] if "\n" in query else query

        return query if validate_cypher(query) else generate_fallback_query(user_question)
    except Exception as e:
        st.error(f"LLM Error: {str(e)}")
        return generate_fallback_query(user_question)

def generate_fallback_query(question: str) -> str:
    """Fallback queries with CORRECTED colons (no backslashes)."""
    question_lower = question.lower()
    if any(word in question_lower for word in ["gluten-free", "celiac"]):
        return "MATCH (p:Product) WHERE 'gluten-free' IN p.tags RETURN p.name, p.description, p.tags"
    if "lactose-free" in question_lower:
        return "MATCH (p:Product) WHERE 'lactose-free' IN p.tags RETURN p.name, p.description, p.tags"
    if "organic" in question_lower:
        return "MATCH (p:Product) WHERE 'organic' IN p.tags RETURN p.name, p.description, p.category"
    if "labneh" in question_lower:
        return "MATCH (p:Product {name: 'Organic Labneh'})-[:AVAILABLE_AT]->(r:Retailer)-[:LOCATED_AT]->(l:Location) RETURN r.name, l.neighborhood, l.address"
    if "hummus" in question_lower:
        return "MATCH (p:Product {name: 'Classic Hummus'})-[:AVAILABLE_AT]->(r:Retailer)-[:LOCATED_AT]->(l:Location) RETURN r.name, l.neighborhood, l.address"
    if any(word in question_lower for word in ["open", "sunday", "5pm"]):
        return "MATCH (r:Retailer)-[:OPEN_AT]->(t:TimeSlot {day: 'Sunday'}) WHERE t.start <= '17:00' AND t.end >= '17:00' RETURN r.name, t.start, t.end, r.location"
    return "MATCH (p:Product) RETURN p.name, p.category LIMIT 10"

def format_answer(results: List[Dict[str, Any]] | str, question: str) -> str:
    """Format results into human-readable answers."""
    if isinstance(results, str):
        return results
    if not results:
        return "No results found."

    question_lower = question.lower()
    if any(word in question_lower for word in ["gluten-free", "lactose-free", "organic", "vegan", "celiac"]):
        products = []
        for record in results:
            if "p" in record:
                name = record["p"].get("name", "Unknown")
                desc = record["p"].get("description", "")
                tags = ", ".join(record["p"].get("tags", []))
                products.append(f"**{name}** - {desc} (*{tags}*)")
        return "\n\n".join(products) if products else "No matching products found."
    elif any(word in question_lower for word in ["where", "location", "near", "find"]):
        locations = []
        for record in results:
            retailer = record.get("r", {}).get("name", "Unknown")
            neighborhood = record.get("l", {}).get("neighborhood", "Unknown")
            address = record.get("l", {}).get("address", "Unknown")
            locations.append(f"- **{retailer}** in {neighborhood}: {address}")
        return "\n".join(locations) if locations else "No locations match your criteria."
    elif any(word in question_lower for word in ["open", "close", "hours", "time"]):
        times = []
        for record in results:
            retailer = record.get("r", {}).get("name", "Unknown")
            day = record.get("t", {}).get("day", "Unknown")
            start = record.get("t", {}).get("start", "?")
            end = record.get("t", {}).get("end", "?")
            times.append(f"- **{retailer}**: {day} {start}–{end}")
        return "\n".join(times) if times else "No matching hours found."
    else:
        items = []
        for record in results:
            if "p" in record:
                items.append(f"- {record['p'].get('name', 'Unknown')}")
            elif "r" in record:
                items.append(f"- {record['r'].get('name', 'Unknown')}")
        return "\n".join(items) if items else "No items found."

def get_product_catalog() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch product catalog with explicit error handling."""
    query = """
    MATCH (p:Product)
    RETURN p.name AS name, p.category AS category, p.tags AS tags
    ORDER BY p.category, p.name
    """
    results = execute_query(query)
    if isinstance(results, str):
        st.error(f"❌ Catalog query failed: {results}")
        return {}
    catalog: Dict[str, List[Dict[str, Any]]] = {}
    for record in results:
        category = record.get("category", "Other")
        if category not in catalog:
            catalog[category] = []
        catalog[category].append({
            "name": record.get("name", "Unknown"),
            "tags": record.get("tags", []),
        })
    return catalog

# --- Streamlit App ---
def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="LibanJus KG Assistant",
        page_icon="🍊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
            /* LibanJus Branding */
            .stApp {
                background-color: #F0F8F0;
            }
            .stChatMessage {
                padding: 1rem;
                border-radius: 0.5rem;
                margin-bottom: 1rem;
                background-color: #FFFFFF;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .stChatMessage p {
                margin: 0;
                color: #2F4F2F;
            }
            .user-message {
                background-color: #E8F5E8 !important;
                margin-left: 20%;
                border-left: 3px solid #2E8B57;
            }
            .assistant-message {
                background-color: #FFFFFF !important;
                margin-right: 20%;
                border-left: 3px solid #4CAF50;
            }
            .stButton>button {
                background-color: #2E8B57 !important;
                color: white !important;
                border: none !important;
            }
            .stButton>button:hover {
                background-color: #267D43 !important;
            }
            .stSidebar {
                background-color: #FFFFFF !important;
            }
            h1, h2, h3 {
                color: #2F4F2F !important;
            }
            .stExpander {
                border: 1px solid #4CAF50 !important;
                border-radius: 0.5rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("🍊 LibanJus Knowledge Graph Assistant")
    st.markdown("*Ask about products, dietary needs, store locations, or opening hours.*")

    # Test connection upfront
    try:
        driver = get_neo4j_driver()
        with driver.session() as s:
            count = s.run("MATCH (p:Product) RETURN count(p)").single()[0]
        st.success(f"✅ Connected to Neo4j! Found {count} products.")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []

    # Test Neo4j connection upfront
    try:
        driver = get_neo4j_driver()
        driver.close()
    except Exception:
        st.error("❌ Cannot connect to Neo4j. Check your .streamlit/secrets.toml file.")
        st.stop()

    with st.sidebar:
        st.header("📚 Product Catalog")
        catalog = get_product_catalog()
        if not catalog:
            st.warning("⚠️ No products found. Did you run `python load_kg_data.py`?")
        else:
            for category, products in catalog.items():
                with st.expander(f"📦 {category}"):
                    for product in products:
                        tags = ", ".join(product["tags"]) if product["tags"] else "No tags"
                        st.markdown(f"**{product['name']}**  \n*Tags: {tags}*")

        st.divider()
        st.header("ℹ️ About")
        st.markdown(
            "**Tech Stack:**\n"
            "- 🗃️ Neo4j 6.2.0 (Knowledge Graph)\n"
            "- 🤖 Mistral AI (Query Generation)\n"
            "- 🎨 Streamlit 1.58.0 (UI)\n"
            "- 🐍 Python 3.12"
        )

        st.markdown("**Try These:**")
        example_questions = [
            "As a celiac, which products can I get?",
            "Where can I get organic Labneh near Al-Hamra?",
            "Is there lactose-free milk?",
            "Which stores are open on Sunday at 5pm?",
        ]
        for q in example_questions:
            if st.button(q, key=f"btn_{hash(q) % 10000}", use_container_width=True):
                st.session_state["user_input"] = q
                st.rerun()

    chat_container = st.container()
    for msg in st.session_state.messages:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question...") or st.session_state.get("user_input"):
        if st.session_state.get("user_input"):
            prompt = st.session_state["user_input"]
            del st.session_state["user_input"]

        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("🤔 Thinking..."):
            cypher_query = generate_cypher(prompt)
            if not cypher_query:
                st.error("Could not generate a query. Please rephrase.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Sorry, I couldn't generate a query. Please try rephrasing.",
                })
                st.rerun()

            results = execute_query(cypher_query)
            answer = format_answer(results, prompt)

        with chat_container.chat_message("assistant"):
            with st.expander("🔍 See Generated Cypher Query"):
                st.code(cypher_query, language="cypher")
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})

    st.sidebar.divider()
    if st.sidebar.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("🔄 Reset Connection", use_container_width=True):
        if "neo4j_driver" in st.session_state:
            del st.session_state.neo4j_driver
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()