
from __future__ import annotations

from typing import List, Dict, Any, Optional
import streamlit as st
import tempfile
import math
from pyvis.network import Network
import networkx as nx

from utils.db import get_neo4j_driver


# --- Graph visual styling ---
# Tier controls the concentric ring each label is placed on (0 = center).
# Color/shape/size drive the legend and the per-node visual encoding.
NODE_STYLES: Dict[str, Dict[str, Any]] = {
    "Product":     {"tier": 0, "color": "#30A9FA", "shape": "dot",      "size": 26},
    "Distributor": {"tier": 1, "color": "#F40000", "shape": "diamond", "size": 20},
    "Factory":     {"tier": 1, "color": "#FFFB1C", "shape": "triangle", "size": 20},
    "Retailer":    {"tier": 2, "color": "#53FD3D", "shape": "dot",      "size": 20},
    # "Location":    {"tier": 3, "color": "#6C757D", "shape": "square",   "size": 14},
    "TimeSlot":    {"tier": 3, "color": "#FF04DE", "shape": "dot",      "size": 10},
}
DEFAULT_NODE_STYLE: Dict[str, Any] = {"tier": 2, "color": "#AAAAAA", "shape": "dot", "size": 16}
RING_SPACING_PX = 180  # distance between concentric tiers


def _node_style(labels) -> Dict[str, Any]:
    """Look up the visual style for a node's primary label."""
    primary = list(labels)[0] if labels else ""
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
                f"""
                MATCH path = (center:Product {{name: $center_node}})-[*1..{max(1, depth)}]-(other)
                WITH relationships(path) AS rels
                UNWIND rels AS r
                WITH DISTINCT r, startNode(r) AS n, endNode(r) AS m
                RETURN n, r, m
                LIMIT $limit
                """,
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
    """Legend with actual node shapes (dot, diamond, triangle, square)."""
    shape_styles = {
        "dot": "border-radius: 50%;",
        "diamond": "transform: rotate(45deg); border-radius: 0%;",
        "triangle": "clip-path: polygon(50% 0%, 0% 100%, 100% 100%); border-radius: 0%;",
        "square": "border-radius: 0%;",
    }
    swatches = []
    for label, style in NODE_STYLES.items():        
        shape = style["shape"]
        shape_style = shape_styles.get(shape, shape_styles[shape])
        swatches.append(
            f'<span style="display:inline-flex;align-items:center;margin-right:1.25rem;">'
            f'<span style="display:inline-block;width:12px;height:12px;{shape_style}'
            f'background:{style["color"]};margin-right:0.4rem;"></span>'
            f'{label}</span>'
        )
    return (
        '<div style="font-size:0.85rem;color:#555;margin-bottom:0.5rem;">'
        + "".join(swatches)
        + "</div>"
    )

