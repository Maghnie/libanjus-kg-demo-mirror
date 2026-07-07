"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
# import requests
import streamlit as st
from neo4j import GraphDatabase, Driver
import google.genai as genai
from google.genai import types

# --- Constants ---
SCHEMA = """
Nodes:
- Product (name, description, ingredients, tags, category, brand)
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
def load_company_config(company_name: str = "libanjus") -> Dict[str, Any]:
    """Load company-specific configuration."""
    config_path = Path(f"config/companies/{company_name}.json")
    if not config_path.exists():
        return {
            "name": company_name,
            "display_name": "LibanJus",
            "description": "Lebanese food products company",
            "icon": "🍊",
            "color": "#2E8B57"
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
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
        tags = session.run("MATCH (p:Product) UNWIND p.tags AS tag RETURN DISTINCT tag").value()
        retailer_names = session.run("MATCH (r:Retailer) RETURN DISTINCT r.name AS name").value()
    return {
        "categories": [c for c in categories if c is not None],
        "brands": [b for b in brands if b is not None],
        "tags": [t for t in tags if t is not None],
        "retailers": [r for r in retailer_names if r is not None],
    }

def validate_cypher(query: str) -> bool:
    """Light validation: must have a RETURN and no dangerous keywords."""
    if not query:
        return False
    q_lower = query.lower().strip()
    # Must contain RETURN, but may also contain ORDER BY, LIMIT, etc.
    if "return" not in q_lower:
        return False
    # Disallow write operations
    dangerous = {"create", "delete", "merge", "set", "remove"}
    if any(word in q_lower for word in dangerous):
        return False
    # Must start with MATCH (most common) or OPTIONAL MATCH, but could be RETURN directly
    if not (q_lower.startswith("match") or q_lower.startswith("optional match") or q_lower.startswith("return")):
        return False
    return True

# def validate_cypher(query: str) -> bool:
#     """Strict validation: must have RETURN/FINISH/UPDATE and no syntax errors."""
#     if not query:
#         return False
#     query_lower = query.lower().strip()
#     # Must start with valid clause and contain RETURN/FINISH/UPDATE
#     if not query_lower.startswith(("match", "return", "create", "finish", "update")):
#         return False
#     if "return" not in query_lower and "finish" not in query_lower and "update" not in query_lower:
#         return False
#     # Reject known bad patterns
#     if "{tags:" in query or "{tags: [" in query:
#         return False
#     return True

# def generate_cypher(user_question: str) -> Optional[str]:
#     """Generate Cypher with strict rules for free tier reliability."""
#     api_key = st.secrets.get("GEMINI_API_KEY")
#     if not api_key:
#         st.error("GEMINI API key not configured")
#         return None

#     prompt = f"""
#     You are a Neo4j Cypher expert.

#     Given the following graph schema, generate a read-only Cypher query to answer the user's question. You MUST follow these rules:

#     Schema: ... (list your nodes, relationships, and properties).

#     Syntax: Use single quotes for strings ('value'). Use aliases like p for Product and r for Retailer.

#     Validity: The query MUST be syntactically correct and end with a RETURN statement.

#     Output: Return ONLY the Cypher query. Do not include any explanations, markdown, or extra text.

#     Example 1:
#     User: "Which stores are open on Sunday at 5pm?"
#     Cypher: MATCH (r:Retailer)-[:OPEN_AT]->(t:TimeSlot {{day: 'Sunday'}}) WHERE t.start <= '17:00' AND t.end >= '17:00' RETURN r.name, t.day, t.start, t.end

#     Example 2:
#     User: "What Maccaw juices are available?"
#     Cypher: MATCH (p:Product)-[:AVAILABLE_AT]->(r:Retailer) WHERE p.brand = 'Maccaw' RETURN p.name, r.name

#     User Question: {user_question}
#     """

#     url = "https://api.mistral.ai/v1/chat/completions"
#     headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
#     payload = {
#         "model": "mistral-tiny",
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 0.5,  
#         "max_tokens": 500,
#     }

#     try:
#         response = requests.post(url, headers=headers, json=payload, timeout=30)
#         response.raise_for_status()
#         query = response.json()["choices"][0]["message"]["content"].strip()

#         # Clean up
#         if "```" in query:
#             query = query.split("```")[1].split("```")[0].strip()
#         if query.startswith(("cypher", "Cypher")):
#             query = query.split("\n")[1] if "\n" in query else query

#         print(query)
#         return query if validate_cypher(query) else generate_fallback_query(user_question)
#     except Exception as e:
#         print(e)
#         return generate_fallback_query(user_question)
    
def generate_cypher(user_question: str) -> Optional[str]:
    """Generate Cypher using Gemini with a strict system prompt."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API key not configured")
        return None

    model_name = st.secrets.get("GEMINI_MODEL", "gemini-3.5-flash")
    client = genai.Client(api_key=api_key)

    # Fetch actual values from the DB
    values = get_distinct_values()
    print(f"Distinct values: {values}")
    categories_str = ", ".join(values["categories"])
    brands_str = ", ".join(values["brands"])
    tags_str = ", ".join(values["tags"])
    retailers_str = ", ".join(values["retailers"])

    # System instruction – defines the task and output format
    system_prompt = f"""
    You are a Neo4j Cypher expert. Your task is to convert a user question into a **valid, read‑only Cypher query**.
    Follow these rules strictly:

    1. **Schema**:
    {SCHEMA}   

    **Important – actual values in the database**:
    - Product.category can be: {categories_str}
    - Product.brand can be: {brands_str}
    - Product.tags can include: {tags_str}
    - Retailer.name can be: {retailers_str}

    2. **Syntax**:
    - Always use these exact category, brand, or tag values as they appear in the database.
    - Use single quotes for strings: 'value'
    - Use aliases: p for Product, r for Retailer, l for Location, t for TimeSlot, etc.
    - Always end the query with a `RETURN` clause.
    - Do not use `CREATE`, `DELETE`, `MERGE`, or any write operations.

    3. **Examples**:
    User: "Which stores are open on Sunday at 5pm?"
    Cypher: MATCH (r:Retailer)-[:OPEN_AT]->(t:TimeSlot {{day: 'Sunday'}}) 
                WHERE t.start <= '17:00' AND t.end >= '17:00' 
                RETURN r.name, t.day, t.start, t.end

    User: "What Maccaw juices are available?"
    Cypher: MATCH (p:Product)-[:AVAILABLE_AT]->(r:Retailer) 
                WHERE p.brand = 'Maccaw' 
                RETURN p.name, r.name

    User: "As a celiac, which products can I get?"
    Cypher: MATCH (p:Product) WHERE 'gluten-free' IN p.tags RETURN p.name, p.tags

    4. **Response**:
    Output **only the Cypher query**. No explanations, no markdown, no backticks.
    """

    prompt = f"User question: {user_question}"

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        )
        print(f"Generated response: {response}")

        query = response.text.strip()

        # Clean up if model still outputs markdown
        if "```" in query:
            parts = query.split("```")
            query = parts[1] if len(parts) > 1 else parts[0]
        if query.lower().startswith("cypher"):
            query = query.split("\n", 1)[-1].strip()

        # Validate
        if validate_cypher(query):
            return query
        else:
            # Fallback if validation fails
            return generate_fallback_query(user_question)

    except Exception as e:
        print(f"Gemini error: {e}")
        return generate_fallback_query(user_question)
    
def generate_fallback_query(question: str) -> str:
    """Fallback queries"""
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
        return "MATCH (r:Retailer)-[:OPEN_AT]->(t:TimeSlot {day: 'Sunday'}) WHERE t.start <= '17:00' AND t.end >= '17:00' RETURN r.name, t.day, t.start, t.end, r.location"
    return "MATCH (p:Product) RETURN p.name, p.category LIMIT 10"

def format_answer(results: List[Dict[str, Any]] | str, question: str) -> str:
    """Format results - handles nested, flat, AND prefixed (p.name) keys."""
    if isinstance(results, str):
        return results
    if not results:
        return "No results found."

    def extract_value(record: Dict[str, Any], field: str) -> Any:
        """Extract a value from a Neo4j record, supporting dotted keys and nested dicts."""
        # 1. Exact match
        if field in record:
            return record[field]
        # 2. Dotted keys like 'r.name' or 'p.description'
        for key, value in record.items():
            if key.endswith(f".{field}"):
                return value
        # 3. Nested dict (e.g., record['p'] = {'name': ...})
        for key, value in record.items():
            if isinstance(value, dict) and field in value:
                return value[field]
        # 4. If record has only one key and it's a dict, try that
        if len(record) == 1:
            only_value = next(iter(record.values()))
            if isinstance(only_value, dict) and field in only_value:
                return only_value[field]
        return None

    question_lower = question.lower()

    if any(word in question_lower for word in ["gluten-free", "lactose-free", "organic", "vegan", "celiac"]):
        products = []
        for record in results:
            name = extract_value(record, "name") or "Unknown"
            desc = extract_value(record, "description") or ""
            tags = extract_value(record, "tags") or []
            products.append(f"**{name}** - {desc} (*{', '.join(tags)}*)")
        return "\n\n".join(products) if products else "No matching products found."

    elif any(word in question_lower for word in ["where", "location", "near", "find"]):
        locations = []
        for record in results:
            retailer = extract_value(record, "name") or extract_value(record, "r") or "Unknown"
            neighborhood = extract_value(record, "neighborhood") or extract_value(record, "l.neighborhood") or "Unknown"
            address = extract_value(record, "address") or extract_value(record, "l.address") or "Unknown"
            locations.append(f"- **{retailer}** in {neighborhood}: {address}")
        return "\n".join(locations) if locations else "No locations match your criteria."

    elif any(word in question_lower for word in ["open", "close", "hours", "time"]):
        times = []
        for record in results:
            retailer = extract_value(record, "name") or extract_value(record, "r") or "Unknown"
            day = extract_value(record, "day") or extract_value(record, "t.day") or "Unknown"
            start = extract_value(record, "start") or extract_value(record, "t.start") or "?"
            end = extract_value(record, "end") or extract_value(record, "t.end") or "?"
            times.append(f"- **{retailer}**: {day} {start}–{end}")
        return "\n".join(times) if times else "No matching hours found."

    else:
        items = []
        for record in results:
            name = extract_value(record, "name") or "Unknown"
            items.append(f"- {name}")
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
    company_config = load_company_config(os.getenv("COMPANY", "libanjus"))
    st.set_page_config(
        page_title=f"{company_config['display_name']} KG Assistant",
        page_icon=company_config.get("icon", "🍊"),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    company_color = company_config.get("color", "#2E8B57")
    st.markdown(f"""
    <style>
        .stApp {{ background-color: #F0F8F0; }}
        .stChatMessage {{ padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; background-color: #FFFFFF; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stChatMessage p {{ margin: 0; color: {company_color}; }}
        .user-message {{ background-color: #E8F5E8 !important; margin-left: 20%; border-left: 3px solid {company_color}; }}
        .assistant-message {{ background-color: #FFFFFF !important; margin-right: 20%; border-left: 3px solid {company_color}; }}
        .stButton>button {{ background-color: {company_color} !important; color: white !important; border: none !important; }}
        .stButton>button:hover {{ background-color: {company_color}CC !important; }}
        .stSidebar {{ background-color: #FFFFFF !important; }}
        h1, h2, h3 {{ color: {company_color} !important; }}
        .stExpander {{ border: 1px solid {company_color} !important; border-radius: 0.5rem !important; }}
    </style>
    """, unsafe_allow_html=True)

    st.title(f"{company_config['icon']} {company_config['display_name']} Knowledge Graph Assistant")
    st.markdown(f"*{company_config['description']}*")

    # Test connection upfront
    try:
        driver = get_neo4j_driver()
        with driver.session() as s:
            count = s.run("MATCH (p:Product) RETURN count(p)").single()[0]
        st.toast(f"Connected to Neo4j database.", icon="✅")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}. Trying refreshing the page.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, str]] = []

    # LOAD CATALOG BEFORE SIDEBAR RENDERS to prevent race condition
    catalog = get_product_catalog()

    with st.sidebar:
        st.header("📚 Product Catalog")        
        if not catalog:
            st.warning("⚠️ No products found. Did you run `python load_kg_data.py`?")
        else:
            for category, products in catalog.items():
                with st.expander(f"📦 {category}"):
                    for product in products:
                        tags = ", ".join(product["tags"]) if product["tags"] else "No tags"
                        st.markdown(f"**{product['name']}**  \n*Tags: {tags}*")

        st.divider()

        st.markdown("**Try These:**")
        example_questions = [
            "As a celiac, which products can I get?",
            "Where can I get organic Labneh near Al-Hamra?",
            "Is there fat-free milk?",
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
            print(results)
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