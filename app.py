"""LibanJus Knowledge Graph Assistant - Streamlit chat interface."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
# import requests
import streamlit as st
from neo4j import GraphDatabase, Driver, RoutingControl, Result
import google.genai as genai
from google.genai import types
# from neo4j_viz.gds import from_gds
from neo4j_viz.neo4j import from_neo4j
import tempfile
import math
from pyvis.network import Network
import networkx as nx

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

# --- Graph visual styling ---
# Tier controls the concentric ring each label is placed on (0 = center).
# Color/shape/size drive the legend and the per-node visual encoding.
NODE_STYLES: Dict[str, Dict[str, Any]] = {
    "Product":     {"tier": 0, "color": "#2E8B57", "shape": "dot",      "size": 26},
    "Distributor": {"tier": 1, "color": "#F4A300", "shape": "diamond", "size": 20},
    "Factory":     {"tier": 1, "color": "#8E5FD9", "shape": "triangle", "size": 20},
    "Retailer":    {"tier": 2, "color": "#3D8BFD", "shape": "dot",      "size": 20},
    "Location":    {"tier": 3, "color": "#6C757D", "shape": "square",   "size": 14},
    "TimeSlot":    {"tier": 3, "color": "#B0B7BF", "shape": "dot",      "size": 10},
}
DEFAULT_NODE_STYLE = {"tier": 2, "color": "#AAAAAA", "shape": "dot", "size": 16}
RING_SPACING_PX = 180  # distance between concentric tiers

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

def get_neo4j_graph():
    # aura_instance_id = st.secrets["AURA_INSTANCEID"]
    # uri = f"neo4j+s://{aura_instance_id}.databases.neo4j.io:7687"
    # auth = (st.secrets["NEO4J_USER"], st.secrets["NEO4J_PASSWORD"])
    # with GraphDatabase.driver(uri, auth=auth) as driver:
    #     driver.verify_connectivity()
    #     result = driver.execute_query(
    #         "MATCH (n)-[r]->(m) RETURN n,r,m",
    #         database_=st.secrets["NEO4J_DATABASE"],
    #         routing_=RoutingControl.READ
    #     )
    # VG = from_neo4j(result)
    driver = get_neo4j_driver()  # reuse your cached driver
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        result = session.run(
            "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 200"  # limit to avoid overload
        )
        # Optional: print record count for debugging
        # records = list(result)
        # st.session_state["graph_record_count"] = len(records)
        # Re‑create result iterator (or pass records if from_neo4j accepts lists)
        # Many implementations accept a Result or a list of Records.
        # If from_neo4j requires a Result, you can't re‑iterate; instead, call session.run again.
        # Safer: pass the list of records if from_neo4j supports it.
        # Check the package docs – often it accepts an iterable of records.
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
        tags = session.run("MATCH (p:Product) UNWIND p.tags AS tag RETURN DISTINCT tag").value()
        retailer_names = session.run("MATCH (r:Retailer) RETURN DISTINCT r.name AS name").value()
    return {
        "categories": [c for c in categories if c is not None],
        "brands": [b for b in brands if b is not None],
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

# @st.cache_data(ttl=3600)
# def fetch_graph_data(limit: int = 200) -> tuple[list, list]:
#     """
#     Fetch graph nodes and relationships from Neo4j.
#     Returns (nodes, edges) where:
#       - nodes: list of dicts with 'id', 'label', and optional 'properties'
#       - edges: list of dicts with 'source', 'target', and 'label'
#     """
#     # Use a limited query to avoid overwhelming the browser
#     query = """
#     MATCH (n)-[r]->(m)
#     RETURN n, r, m
#     LIMIT $limit
#     """
#     result = execute_query(query, params={"limit": limit})
#     if isinstance(result, str):  # error string
#         st.error(f"Graph query failed: {result}")
#         return [], []

#     nodes = {}
#     edges = []
#     for record in result:
#         # Each record has keys: 'n', 'r', 'm' (from the query)
#         n = record["n"]
#         m = record["m"]
#         r = record["r"]

#         # Add source node
#         nodes[n.element_id] = { #element_id from neo4j internal ID system
#             "id": n.element_id,
#             "label": list(n.labels)[0] if n.labels else "Node",
#             "properties": dict(n.items()),  # includes name, etc.
#         }
#         # Add target node
#         nodes[m.element_id] = {
#             "id": m.element_id,
#             "label": list(m.labels)[0] if m.labels else "Node",
#             "properties": dict(m.items()),
#         }
#         # Add relationship
#         edges.append({
#             "source": n.element_id,
#             "target": m.element_id,
#             "label": r.type,
#         })

#     return list(nodes.values()), edges

def _node_style(labels) -> Dict[str, Any]:
    """Look up the visual style for a node's primary label."""
    primary = list(labels)[0] if labels else None
    return NODE_STYLES.get(primary, DEFAULT_NODE_STYLE)

def _compute_tiered_layout(G: "nx.Graph", center_id: Optional[str] = None) -> Dict[str, tuple]:
    """
    Deterministic concentric layout.

    When `center_id` is given (product-focused view), the ring a node
    lands on is its graph-hop distance from that node — so the chosen
    product is always alone at the origin and everything else fans out
    by how far it actually is from it, regardless of label. This is what
    gives the view real "focus": without it, sibling Products reached via
    a shared Distributor/Factory would incorrectly get pulled to the
    center ring too (label-based tiering can't tell a focus node from a
    same-labeled neighbor).

    When no center is given (global view), falls back to the static
    label-based tier (Product -> Factory/Distributor -> Retailer ->
    Location/TimeSlot) stored on each node as "label_tier".

    Either way this is computed once in plain Python — no simulation, no
    settling time, identical output every rerun.
    """
    if center_id is not None and center_id in G:
        distances = nx.single_source_shortest_path_length(G, center_id)
        max_known = max(distances.values(), default=0)
        tier_of = lambda node_id: distances.get(node_id, max_known + 1)
    else:
        tier_of = lambda node_id: G.nodes[node_id].get("label_tier", DEFAULT_NODE_STYLE["tier"])

    tiers: Dict[int, List[str]] = {}
    for node_id in G.nodes:
        tiers.setdefault(tier_of(node_id), []).append(node_id)

    pos: Dict[str, tuple] = {}
    for tier, node_ids in sorted(tiers.items()):
        radius = tier * RING_SPACING_PX
        count = len(node_ids)
        if radius == 0:
            # The focus node (or, in global view, all Product nodes) sits at the origin.
            for i, node_id in enumerate(node_ids):
                offset = 40 * i  # nudge apart only if more than one lands here
                pos[node_id] = (offset, 0)
            continue
        for i, node_id in enumerate(node_ids):
            angle = (2 * math.pi * i) / count
            pos[node_id] = (radius * math.cos(angle), radius * math.sin(angle))
    return pos

@st.cache_data(ttl=3600)
def get_pyvis_graph(
    limit: int = 200,
    center_node: Optional[str] = None,
    depth: int = 2,
) -> str:
    """
    Fetch graph data from Neo4j and render it as a static, styled PyVis
    HTML string.

    If `center_node` is given, the query is scoped to that Product's
    ego-network up to `depth` hops (keeps the default view small and
    legible). Otherwise it falls back to a global, limited sample.

    The layout is precomputed in Python (concentric rings by hop-distance
    from the focus product, or by label in global view) and handed to
    vis.js with physics disabled — so the graph is perfectly stationary
    and identical on every rerun, instead of depending on a force
    simulation that never fully settles. Nodes stay manually draggable;
    only the automatic physics-driven movement is turned off.
    """
    driver = get_neo4j_driver()
    with driver.session(database=st.secrets.get("NEO4J_DATABASE", "neo4j")) as session:
        if center_node:
            result = session.run(
                """
                MATCH path = (center:Product {name: $center_node})-[*1..%d]-(other)
                WITH relationships(path) AS rels
                UNWIND rels AS r
                WITH DISTINCT r, startNode(r) AS n, endNode(r) AS m
                RETURN n, r, m
                LIMIT $limit
                """ % max(1, depth),
                center_node=center_node,
                limit=limit,
            )
        else:
            result = session.run(
                """
                MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
                """,
                limit=limit,
            )
        records = list(result)

    if not records:
        return "<p>No graph data found for this selection.</p>"

    # --- Build a networkx graph purely to compute a deterministic layout ---
    G = nx.Graph()
    node_meta: Dict[str, Dict[str, Any]] = {}
    center_id: Optional[str] = None

    for record in records:
        n, m, r = record["n"], record["m"], record["r"]
        for node in (n, m):
            if node.element_id not in node_meta:
                style = _node_style(node.labels)
                label = node.get("name") or (list(node.labels)[0] if node.labels else "Node")
                is_center = bool(center_node) and "Product" in node.labels and label == center_node
                if is_center:
                    center_id = node.element_id
                node_meta[node.element_id] = {
                    "label": label,
                    "group": list(node.labels)[0] if node.labels else "Node",
                    "is_center": is_center,
                    **style,
                }
                G.add_node(node.element_id, label_tier=style["tier"])
        G.add_edge(n.element_id, m.element_id)

    positions = _compute_tiered_layout(G, center_id=center_id)

    # --- Build the PyVis network with physics fully disabled ---
    net = Network(height="650px", width="100%", directed=True, notebook=False)

    for node_id, meta in node_meta.items():
        x, y = positions.get(node_id, (0, 0))
        node_kwargs = dict(
            label=meta["label"],
            title=f"{meta['group']}: {meta['label']}" + (" ★ focus" if meta["is_center"] else ""),
            shape=meta["shape"],
            size=meta["size"] + (8 if meta["is_center"] else 0),
            group=meta["group"],
            x=x,
            y=y,
            physics=False,   # stops the physics engine from moving it...
            # ...but we deliberately do NOT set "fixed": vis.js treats
            # "fixed" as also blocking manual drag, which is why nodes
            # were frozen in place and un-draggable before. Leaving nodes
            # un-fixed with physics disabled means: no automatic drift,
            # but the person can still pick up and reposition any node.
        )
        if meta["is_center"]:
            node_kwargs["color"] = {"background": meta["color"], "border": "#B8860B", "highlight": {"background": meta["color"], "border": "#B8860B"}}
            node_kwargs["borderWidth"] = 4
        else:
            node_kwargs["color"] = meta["color"]
        net.add_node(node_id, **node_kwargs)

    for record in records:
        n, m, r = record["n"], record["m"], record["r"]
        net.add_edge(
            n.element_id,
            m.element_id,
            title=r.type,          # relationship type shows on hover only
            color="#C7CCD1",
            arrows="to",
            width=1,
        )

    # Physics off globally too (belt-and-braces alongside per-node "physics": False).
    # Edge labels are hidden by default (font size 0) to kill the label clutter;
    # hovering a node/edge reveals its `title` tooltip instead.
    net.set_options("""
    {
      "physics": { "enabled": false },
      "layout": { "improvedLayout": false },
      "edges": {
        "font": { "size": 0 },
        "smooth": { "type": "continuous" },
        "color": { "inherit": false }
      },
      "nodes": {
        "font": { "size": 14, "face": "Inter, Arial, sans-serif" }
      },
      "interaction": {
        "hover": true,
        "dragNodes": true,
        "zoomView": true,
        "tooltipDelay": 100
      }
    }
    """)

    # Generate HTML in memory
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, "r", encoding="utf-8") as f:
            html_content = f.read()
    return html_content

def get_graph_legend_html() -> str:
    """Small colored-dot legend matching NODE_STYLES, for display above the graph."""
    swatches = []
    for label, style in NODE_STYLES.items():
        shape_note = "" if style["shape"] == "dot" else f" ({style['shape']})"
        swatches.append(
            f'<span style="display:inline-flex;align-items:center;margin-right:1.25rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
            f'background:{style["color"]};margin-right:0.4rem;"></span>'
            f'{label}{shape_note}</span>'
        )
    return (
        '<div style="font-size:0.85rem;color:#555;margin-bottom:0.5rem;">'
        + "".join(swatches)
        + "</div>"
    )

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

    tab_catalog, tab_chat, tab_graph = st.tabs(["🗃 Data", 
                                                "💬 Chat", 
                                                "🌐 Interactive Graph"], 
                                                default="🌐 Interactive Graph")

    with tab_catalog:
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
        if st.button("🔄 Reset Connection", use_container_width=True):
            if "neo4j_driver" in st.session_state:
                del st.session_state.neo4j_driver
            st.cache_data.clear()
            st.rerun()

    with tab_chat:
        col_sample_qs, col_chat_box = st.columns(2)
        
        with col_sample_qs:
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

        with col_chat_box:
            st.markdown("**Or start typing:**")
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

        st.divider()
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with tab_graph:
        st.header("🌐 Interactive Knowledge Graph")

        col_controls, col_graph = st.columns([1, 3])

        with col_controls:
            st.markdown("**Focus**")
            product_names = get_product_names()
            show_all = st.checkbox("Show full graph (no focus product)", value=False)
            center_node = None
            if not show_all and product_names:
                center_node = st.selectbox("Product", product_names, index=0)
            depth = st.slider(
                "Hops from focus product",
                min_value=1, max_value=4, value=2,
                help="How many relationship hops out from the product to include.",
                disabled=show_all,
            )
            limit = st.slider(
                "Max relationships",
                min_value=25, max_value=200, value=100, step=25,
                help="Caps how many edges are pulled, to keep the graph legible.",
            )
            st.caption("Layout is static (no physics) — drag a node to reposition it; it will stay put.")

        with col_graph:
            st.markdown(get_graph_legend_html(), unsafe_allow_html=True)
            with st.spinner("Building graph..."):
                try:
                    html = get_pyvis_graph(
                        limit=limit,
                        center_node=center_node,
                        depth=depth,
                    )
                    if html and len(html) > 100:
                        st.iframe(html, height=650)
                    else:
                        st.warning("No graph data to display for this selection.")
                except Exception as e:
                    st.error(f"Failed to render graph: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()