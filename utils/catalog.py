from typing import List, Dict, Any
import streamlit as st

from utils.db import execute_query


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