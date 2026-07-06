"""Load sample data into Neo4j Knowledge Graph for LibanJus demo."""

from __future__ import annotations

import os
import sys
from typing import List, Dict, Any
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# --- Data Definitions ---
PRODUCTS: List[Dict[str, Any]] = [
    {
        "name": "Organic Labneh",
        "description": "Premium organic strained yogurt",
        "ingredients": ["Organic Milk", "Salt", "Live Cultures"],
        "tags": ["organic", "gluten-free", "vegetarian"],
        "category": "Dairy",
    },
    {
        "name": "Fat-Free Milk",
        "description": "100% fat-free pasteurized milk",
        "ingredients": ["Skimm Milk", "Vitamin D"],
        "tags": ["fat-free", "lactose-free", "gluten-free"],
        "category": "Dairy",
    },
    {
        "name": "Classic Hummus",
        "description": "Creamy chickpea dip",
        "ingredients": ["Chickpeas", "Tahini", "Lemon Juice", "Garlic"],
        "tags": ["gluten-free", "vegan", "vegetarian"],
        "category": "Dips & Spreads",
    },
]

LOCATIONS: List[Dict[str, Any]] = [
    {"address": "Al-Hamra Main Street, Beirut", "city": "Beirut", "neighborhood": "Al-Hamra", "lat": 33.8938, "lon": 35.4955},
    {"address": "Gemmayzeh Street, Beirut", "city": "Beirut", "neighborhood": "Gemmayzeh", "lat": 33.8919, "lon": 35.5018},
]

RETAILERS: List[Dict[str, Any]] = [
    {
        "name": "ABC Supermarket Al-Hamra",
        "location": "Al-Hamra Main Street, Beirut",
        "opening_hours": [{"day": "Sunday", "start": "09:00", "end": "21:00"}],
    },
    {
        "name": "Spinneys Gemmayzeh",
        "location": "Gemmayzeh Street, Beirut",
        "opening_hours": [{"day": "Sunday", "start": "08:00", "end": "22:00"}],
    },
]

FACTORIES: List[Dict[str, str]] = [{"name": "LibanJus Beirut Factory", "location": "Al-Hamra Main Street, Beirut"}]
DISTRIBUTORS: List[Dict[str, str]] = [{"name": "Beirut Food Distributors", "location": "Sassine Square, Achrafieh, Beirut"}]

PRODUCT_RETAILERS: Dict[str, List[str]] = {
    "Organic Labneh": ["ABC Supermarket Al-Hamra", "Spinneys Gemmayzeh"],
    "Fat-Free Milk": ["ABC Supermarket Al-Hamra"],
    "Classic Hummus": ["ABC Supermarket Al-Hamra", "Spinneys Gemmayzeh"],
}

def load_data(uri: str, user: str, password: str, database: str = "neo4j") -> bool:
    """Load data into Neo4j. Returns True if successful."""
    try:
        driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=database) as session:
            # Test connection first
            session.run("RETURN 1")

            # Clear and load data
            session.run("MATCH (n) DETACH DELETE n")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Retailer) REQUIRE r.name IS UNIQUE")

            for loc in LOCATIONS:
                session.run("CREATE (l:Location {address: $address, city: $city, neighborhood: $neighborhood, lat: $lat, lon: $lon})", **loc)

            for factory in FACTORIES:
                session.run("CREATE (f:Factory {name: $name, location: $location})", **factory)

            for distributor in DISTRIBUTORS:
                session.run("CREATE (d:Distributor {name: $name, location: $location})", **distributor)

            for product in PRODUCTS:
                session.run("CREATE (p:Product {name: $name, description: $description, ingredients: $ingredients, tags: $tags, category: $category})", **product)

            for retailer in RETAILERS:
                session.run("CREATE (r:Retailer {name: $name, location: $location})", name=retailer["name"], location=retailer["location"])
                for hour in retailer["opening_hours"]:
                    session.run("MATCH (r:Retailer {name: $name}) CREATE (r)-[:OPEN_AT]->(t:TimeSlot {day: $day, start: $start, end: $end})", name=retailer["name"], **hour)

            for retailer in RETAILERS:
                session.run("MATCH (r:Retailer {name: $name}) MATCH (l:Location {address: $address}) CREATE (r)-[:LOCATED_AT]->(l)", name=retailer["name"], address=retailer["location"])

            for product_name, retailer_names in PRODUCT_RETAILERS.items():
                for retailer_name in retailer_names:
                    session.run("MATCH (p:Product {name: $product_name}) MATCH (r:Retailer {name: $retailer_name}) CREATE (p)-[:AVAILABLE_AT]->(r)", product_name=product_name, retailer_name=retailer_name)

        driver.close()
        return True
    except Exception as e:
        print(f"❌ Error loading data: {str(e)}", file=sys.stderr)
        return False

def main() -> None:
    """Main entry point with explicit error messages."""
    aura_instance_id = os.getenv("AURA_INSTANCEID")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not aura_instance_id:
        print("❌ Error: AURA_INSTANCEID environment variable not set.", file=sys.stderr)
        print("   Set it in your .env file or export it.", file=sys.stderr)
        sys.exit(1)
    if not neo4j_password:
        print("❌ Error: NEO4J_PASSWORD environment variable not set.", file=sys.stderr)
        print("   Set it in your .env file or export it.", file=sys.stderr)
        sys.exit(1)

    uri = f"neo4j+s://{aura_instance_id}.databases.neo4j.io:7687"
    print(f"🔌 Connecting to Neo4j at {uri}...")

    if load_data(uri, neo4j_user, neo4j_password, neo4j_database):
        print("✅ KG data loaded successfully!")
        print("📊 Verify your data in Neo4j Aura dashboard: https://neo4j.io/aura")
    else:
        print("❌ Failed to load data. Check your connection details.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()