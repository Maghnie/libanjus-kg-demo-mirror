
import json

from typing import List, Dict, Any, Optional
import streamlit as st
import google.genai as genai
from google.genai import types

from utils.db import get_distinct_values


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

# --- Helper Function ---
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

def generate_cypher(user_question: str) -> Optional[str]:
    """Generate Cypher using Gemini with a strict system prompt."""
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API key not configured")
        return None

    model_name = st.secrets.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
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
                max_output_tokens=8192,
                # thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.HIGH)
            )
        )
        print(f"Generated response: {response}")

        if isinstance(response.text, str):
            query = response.text.strip()
        else:
            query = str(response.text).strip()

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
            print(f"Generated query invalid: {query}")
            # Fallback if validation fails
            return None # generate_fallback_query(user_question)

    except Exception as e:
        # st.error(f"Gemini error: {e}")
        return str(e) # generate_fallback_query(user_question)

def format_answer(results: List[Dict[str, Any]] | str, question: str) -> str:
    """Turn raw Cypher results into a natural-language answer via Gemini."""
    if isinstance(results, str):
        return results  # already an error message from execute_query

    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API key not configured. Please set GEMINI_API_KEY in .streamlit/secrets.toml")
        return "\n".join(f"- {r}" for r in results)  # crude but functional fallback

    def _normalize(value: Any) -> Any:
        """Flatten Neo4j Node/Relationship objects to plain dicts."""
        if hasattr(value, "items") and hasattr(value, "labels"):  # Node-like
            return dict(value)
        if isinstance(value, list):
            return [_normalize(v) for v in value]
        return value

    normalized = [{k: _normalize(v) for k, v in r.items()} for r in results]

    MAX_RECORDS = 50
    truncated = len(normalized) > MAX_RECORDS
    payload = normalized[:MAX_RECORDS]

    client = genai.Client(api_key=api_key)
    model_name = st.secrets.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

    prompt = f"""
    A user asked: "{question}"

    The knowledge graph returned these results (JSON){" — showing first "
    + str(MAX_RECORDS) + " of " + str(len(normalized)) if truncated else ""}:
    {json.dumps(payload, default=str)}

    Write a concise, friendly answer using ONLY and ALL OF the data above.
    Use markdown. Do not invent products, retailers, or facts not present in the results.
    
    If the results are empty or irrelevant, say so plainly. Explain that the data is a demo, 
    suggest the user try a different wording, and optionally mention any similar products 
    that exist (based on the schema you know). 
    """

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=8192),
        )
        text = response.text
        if isinstance(text, str) and text.strip():
            return text.strip()
        return "\n".join(f"- {r}" for r in results)  # fallback if empty/blocked
    except Exception as e:
        print(f"format_answer Gemini error: {e}")
        return "\n".join(f"- {r}" for r in results)  # fallback on API failure