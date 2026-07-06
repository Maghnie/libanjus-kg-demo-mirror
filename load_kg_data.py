"""Load company data into Neo4j Knowledge Graph."""

from __future__ import annotations

import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

load_dotenv()

def load_json_file(filepath: Path) -> List[Dict[str, Any]] | Dict[str, Any]:
    """Load a JSON file from the data directory."""
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def get_company_data(company_name: str = "libanjus") -> Dict[str, Any]:
    """Load all data files for a specific company."""
    data_dir = Path(f"data/{company_name}")

    # Load all data files
    products = load_json_file(data_dir / "products.json")
    locations = load_json_file(data_dir / "locations.json")
    retailers = load_json_file(data_dir / "retailers.json")
    factories = load_json_file(data_dir / "factories.json")
    distributors = load_json_file(data_dir / "distributors.json")
    relationships = load_json_file(data_dir / "relationships.json")

    return {
        "products": products,
        "locations": locations,
        "retailers": retailers,
        "factories": factories,
        "distributors": distributors,
        "relationships": relationships,
    }

def load_data(company_name: str = "libanjus") -> bool:
    """Load company data into Neo4j Knowledge Graph."""
    try:
        data = get_company_data(company_name)
        products = data["products"]
        locations = data["locations"]
        retailers = data["retailers"]
        factories = data["factories"]
        distributors = data["distributors"]
        relationships = data["relationships"]

        # Get Neo4j credentials from environment
        aura_instance_id = os.getenv("AURA_INSTANCEID")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

        if not aura_instance_id:
            print("❌ Error: AURA_INSTANCEID environment variable not set.", file=sys.stderr)
            return False
        if not neo4j_password:
            print("❌ Error: NEO4J_PASSWORD environment variable not set.", file=sys.stderr)
            return False

        uri = f"neo4j+s://{aura_instance_id}.databases.neo4j.io:7687"
        driver: Driver = GraphDatabase.driver(uri, auth=(neo4j_user, neo4j_password))

        with driver.session(database=neo4j_database) as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")

            # Create constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Retailer) REQUIRE r.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.address IS UNIQUE")

            # Load locations
            print("📍 Loading locations...")
            for loc in locations:
                session.run(
                    """
                    CREATE (l:Location {
                        address: $address,
                        city: $city,
                        neighborhood: $neighborhood,
                        lat: $lat,
                        lon: $lon
                    })
                    """,
                    **loc,
                )

            # Load factories
            print("🏭 Loading factories...")
            for factory in factories:
                session.run("CREATE (f:Factory {name: $name, location: $location})", **factory)

            # Load distributors
            print("🚚 Loading distributors...")
            for distributor in distributors:
                session.run("CREATE (d:Distributor {name: $name, location: $location})", **distributor)

            # Load products
            print("📦 Loading products...")
            for product in products:
                session.run(
                    """
                    CREATE (p:Product {
                        name: $name,
                        description: $description,
                        ingredients: $ingredients,
                        tags: $tags,
                        category: $category
                    })
                    """,
                    **product,
                )

            # Load retailers + time slots
            print("🏪 Loading retailers...")
            for retailer in retailers:
                session.run(
                    "CREATE (r:Retailer {name: $name, location: $location})",
                    name=retailer["name"],
                    location=retailer["location"],
                )
                for hour in retailer.get("opening_hours", []):
                    session.run(
                        """
                        MATCH (r:Retailer {name: $name})
                        CREATE (r)-[:OPEN_AT]->(t:TimeSlot {
                            day: $day,
                            start: $start,
                            end: $end
                        })
                        """,
                        name=retailer["name"],
                        **hour,
                    )

            # Link retailers to locations
            print("🔗 Linking retailers to locations...")
            for retailer in retailers:
                session.run(
                    """
                    MATCH (r:Retailer {name: $name})
                    MATCH (l:Location {address: $address})
                    CREATE (r)-[:LOCATED_AT]->(l)
                    """,
                    name=retailer["name"],
                    address=retailer["location"],
                )

            # Link products to factories
            print("🔗 Linking products to factories...")
            for product_name, factory_name in relationships.get("product_factories", {}).items():
                session.run(
                    """
                    MATCH (p:Product {name: $product_name})
                    MATCH (f:Factory {name: $factory_name})
                    CREATE (p)-[:MANUFACTURED_AT]->(f)
                    """,
                    product_name=product_name,
                    factory_name=factory_name,
                )

            # Link products to distributors
            print("🔗 Linking products to distributors...")
            for product_name, distributor_name in relationships.get("product_distributors", {}).items():
                session.run(
                    """
                    MATCH (p:Product {name: $product_name})
                    MATCH (d:Distributor {name: $distributor_name})
                    CREATE (p)-[:DISTRIBUTED_BY]->(d)
                    """,
                    product_name=product_name,
                    distributor_name=distributor_name,
                )

            # Link distributors to retailers
            print("🔗 Linking distributors to retailers...")
            for distributor_name, retailer_names in relationships.get("distributor_retailers", {}).items():
                for retailer_name in retailer_names:
                    session.run(
                        """
                        MATCH (d:Distributor {name: $distributor_name})
                        MATCH (r:Retailer {name: $retailer_name})
                        CREATE (d)-[:SUPPLIES_TO]->(r)
                        """,
                        distributor_name=distributor_name,
                        retailer_name=retailer_name,
                    )

            # Link products to retailers
            print("🔗 Linking products to retailers...")
            for product_name, retailer_names in relationships.get("product_retailers", {}).items():
                for retailer_name in retailer_names:
                    session.run(
                        """
                        MATCH (p:Product {name: $product_name})
                        MATCH (r:Retailer {name: $retailer_name})
                        CREATE (p)-[:AVAILABLE_AT]->(r)
                        """,
                        product_name=product_name,
                        retailer_name=retailer_name,
                    )

        driver.close()
        print(f"✅ {company_name} data loaded successfully!")
        return True

    except Exception as e:
        print(f"❌ Error loading {company_name} data: {str(e)}", file=sys.stderr)
        return False

def main() -> None:
    """Main entry point."""
    company_name = os.getenv("COMPANY", "libanjus")
    if not load_data(company_name):
        sys.exit(1)

if __name__ == "__main__":
    main()