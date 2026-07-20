import os

from neo4j import GraphDatabase


NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://neo4j:7687",
)

NEO4J_USER = os.getenv(
    "NEO4J_USER",
    "neo4j",
)

NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


if not NEO4J_PASSWORD:
    raise RuntimeError(
        "La variable NEO4J_PASSWORD n'est pas définie."
    )


driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD),
)


hotels = [
    {
        "id": "hotel-001",
        "name": "Hôtel Centre Casablanca",
        "address": "Centre-ville, Casablanca",
        "latitude": 33.5731,
        "longitude": -7.5898,
        "stars": 4,
    },
    {
        "id": "hotel-002",
        "name": "Hôtel Maarif",
        "address": "Maarif, Casablanca",
        "latitude": 33.5862,
        "longitude": -7.6327,
        "stars": 3,
    },
    {
        "id": "hotel-003",
        "name": "Hôtel Ain Diab",
        "address": "Ain Diab, Casablanca",
        "latitude": 33.5945,
        "longitude": -7.6762,
        "stars": 5,
    },
    {
        "id": "hotel-004",
        "name": "Hôtel Bourgogne",
        "address": "Bourgogne, Casablanca",
        "latitude": 33.5987,
        "longitude": -7.6435,
        "stars": 4,
    },
    {
        "id": "hotel-005",
        "name": "Hôtel Habous",
        "address": "Quartier Habous, Casablanca",
        "latitude": 33.5662,
        "longitude": -7.6043,
        "stars": 3,
    },
    {
        "id": "hotel-006",
        "name": "Hôtel Casa Port",
        "address": "Casa Port, Casablanca",
        "latitude": 33.5993,
        "longitude": -7.6127,
        "stars": 4,
    },
]


def create_constraints_and_indexes() -> None:
    """
    Créer une contrainte d'unicité et un index géographique.
    """

    driver.execute_query(
        """
        CREATE CONSTRAINT hotel_id_unique IF NOT EXISTS
        FOR (h:Hotel)
        REQUIRE h.id IS UNIQUE
        """,
        database_="neo4j",
    )

    driver.execute_query(
        """
        CREATE POINT INDEX hotel_location_index IF NOT EXISTS
        FOR (h:Hotel)
        ON (h.location)
        """,
        database_="neo4j",
    )

    print("Contrainte et index géographique créés.")


def insert_hotels() -> None:
    """
    Insérer ou mettre à jour les hôtels de démonstration.
    """

    query = """
    UNWIND $hotels AS hotel

    MERGE (h:Hotel {id: hotel.id})

    SET h.name = hotel.name,
        h.address = hotel.address,
        h.stars = hotel.stars,
        h.location = point({
            latitude: hotel.latitude,
            longitude: hotel.longitude
        })

    MERGE (city:City {name: "Casablanca"})
    MERGE (h)-[:LOCATED_IN]->(city)
    """

    driver.execute_query(
        query,
        hotels=hotels,
        database_="neo4j",
    )

    print(f"{len(hotels)} hôtels insérés dans Neo4j.")


def verify_data() -> None:
    """
    Afficher les hôtels présents dans Neo4j.
    """

    records, _, _ = driver.execute_query(
        """
        MATCH (h:Hotel)

        RETURN
            h.name AS name,
            h.address AS address,
            h.stars AS stars,
            h.location.latitude AS latitude,
            h.location.longitude AS longitude

        ORDER BY h.name
        """,
        database_="neo4j",
    )

    print("\nHôtels enregistrés :")

    for record in records:
        print(
            f"- {record['name']} | "
            f"{record['stars']} étoiles | "
            f"{record['latitude']}, "
            f"{record['longitude']}"
        )


def main() -> None:
    try:
        driver.verify_connectivity()

        print("Connexion à Neo4j réussie.")

        create_constraints_and_indexes()
        insert_hotels()
        verify_data()

    except Exception as error:
        print(f"Erreur pendant l'initialisation : {error}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()