import os
import re
import time
from typing import Any

import requests
from neo4j import GraphDatabase


# ============================================================
# CONFIGURATION NEO4J
# ============================================================

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
    auth=(
        NEO4J_USER,
        NEO4J_PASSWORD,
    ),
)


# ============================================================
# CONFIGURATION OPENSTREETMAP / OVERPASS
# ============================================================

# Plusieurs serveurs sont utilisés pour éviter qu'un seul serveur
# indisponible bloque complètement l'importation.
OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

# Centre approximatif de Casablanca
CENTER_LATITUDE = 33.5731
CENTER_LONGITUDE = -7.5898

# Rayon d'importation en mètres
# 10000 mètres = 10 kilomètres
IMPORT_RADIUS = 10000

# Nombre de tentatives pour chaque serveur
MAX_ATTEMPTS_PER_SERVER = 3

# Taille d'un lot envoyé à Neo4j
BATCH_SIZE = 200


# ============================================================
# CRÉATION DE LA REQUÊTE OVERPASS
# ============================================================

def build_overpass_query() -> str:
    """
    Construire une requête Overpass permettant de récupérer
    les hôtels autour de Casablanca.
    """

    return f"""
    [out:json][timeout:120];

    (
        node["tourism"="hotel"]
            (around:{IMPORT_RADIUS},
            {CENTER_LATITUDE},
            {CENTER_LONGITUDE});

        way["tourism"="hotel"]
            (around:{IMPORT_RADIUS},
            {CENTER_LATITUDE},
            {CENTER_LONGITUDE});

        relation["tourism"="hotel"]
            (around:{IMPORT_RADIUS},
            {CENTER_LATITUDE},
            {CENTER_LONGITUDE});
    );

    out center tags;
    """


# ============================================================
# TÉLÉCHARGEMENT DES DONNÉES OPENSTREETMAP
# ============================================================

def fetch_osm_hotels() -> list[dict[str, Any]]:
    """
    Télécharger les hôtels depuis OpenStreetMap.

    La fonction essaie plusieurs serveurs Overpass.
    Elle répète également la requête en cas d'erreur temporaire.
    """

    query = build_overpass_query()

    headers = {
        "User-Agent": (
            "geolocation-project/1.0 "
            "(educational student project)"
        ),
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    with requests.Session() as session:
        session.headers.update(headers)

        for server_url in OVERPASS_URLS:
            print()
            print("=" * 65)
            print(f"Serveur Overpass : {server_url}")
            print("=" * 65)

            for attempt in range(
                1,
                MAX_ATTEMPTS_PER_SERVER + 1,
            ):
                try:
                    print(
                        f"Tentative "
                        f"{attempt}/{MAX_ATTEMPTS_PER_SERVER}..."
                    )

                    response = session.post(
                        server_url,
                        data={
                            "data": query,
                        },
                        timeout=(
                            20,
                            180,
                        ),
                    )

                    response.raise_for_status()

                    data = response.json()

                    elements = data.get(
                        "elements",
                        [],
                    )

                    print(
                        f"Réponse reçue : "
                        f"{len(elements)} élément(s)."
                    )

                    return elements

                except requests.Timeout as error:
                    last_error = error

                    print(
                        "Le serveur a dépassé le délai "
                        "de réponse."
                    )

                except requests.ConnectionError as error:
                    last_error = error

                    print(
                        "Impossible de se connecter "
                        "au serveur."
                    )

                except requests.HTTPError as error:
                    last_error = error

                    status_code = (
                        error.response.status_code
                        if error.response is not None
                        else None
                    )

                    print(
                        f"Erreur HTTP : {status_code}"
                    )

                    # Ces erreurs sont généralement temporaires.
                    retryable_status_codes = {
                        429,
                        500,
                        502,
                        503,
                        504,
                    }

                    if (
                        status_code
                        not in retryable_status_codes
                    ):
                        print(
                            "Cette erreur ne semble pas "
                            "temporaire."
                        )
                        break

                except ValueError as error:
                    last_error = error

                    print(
                        "Le serveur n'a pas retourné "
                        "un document JSON valide."
                    )

                except requests.RequestException as error:
                    last_error = error

                    print(
                        "Erreur pendant la communication : "
                        f"{error}"
                    )

                if attempt < MAX_ATTEMPTS_PER_SERVER:
                    waiting_time = 5 * (
                        2 ** (attempt - 1)
                    )

                    print(
                        f"Nouvelle tentative dans "
                        f"{waiting_time} seconde(s)..."
                    )

                    time.sleep(waiting_time)

            print(
                "Le serveur actuel n'a pas répondu. "
                "Passage au serveur suivant."
            )

    raise RuntimeError(
        "Aucun serveur Overpass n'a répondu correctement. "
        f"Dernière erreur : {last_error}"
    )


# ============================================================
# EXTRACTION DES COORDONNÉES
# ============================================================

def extract_coordinates(
    element: dict[str, Any],
) -> tuple[float | None, float | None]:
    """
    Extraire les coordonnées d'un objet OpenStreetMap.

    Les objets de type node contiennent directement lat et lon.
    Les ways et relations utilisent généralement center.
    """

    if element.get("type") == "node":
        latitude = element.get("lat")
        longitude = element.get("lon")

        return latitude, longitude

    center = element.get("center", {})

    latitude = center.get("lat")
    longitude = center.get("lon")

    return latitude, longitude


# ============================================================
# CONSTRUCTION DE L'ADRESSE
# ============================================================

def build_address(
    tags: dict[str, Any],
) -> str:
    """
    Construire une adresse lisible à partir des tags OSM.
    """

    address_parts: list[str] = []

    house_number = tags.get("addr:housenumber")
    street = tags.get("addr:street")
    neighbourhood = tags.get("addr:neighbourhood")
    suburb = tags.get("addr:suburb")
    postcode = tags.get("addr:postcode")
    city = tags.get("addr:city")

    if house_number:
        address_parts.append(
            str(house_number)
        )

    if street:
        address_parts.append(
            str(street)
        )

    if neighbourhood:
        address_parts.append(
            str(neighbourhood)
        )

    if suburb:
        address_parts.append(
            str(suburb)
        )

    if postcode:
        address_parts.append(
            str(postcode)
        )

    if city:
        address_parts.append(
            str(city)
        )

    if not address_parts:
        return "Adresse non disponible"

    return ", ".join(address_parts)


# ============================================================
# EXTRACTION DU NOMBRE D'ÉTOILES
# ============================================================

def extract_stars(
    tags: dict[str, Any],
) -> int | None:
    """
    Extraire le nombre d'étoiles de l'hôtel.

    OpenStreetMap peut enregistrer cette information dans
    plusieurs propriétés.
    """

    raw_stars = (
        tags.get("stars")
        or tags.get("hotel:stars")
    )

    if raw_stars is None:
        return None

    match = re.search(
        r"\b([1-5])\b",
        str(raw_stars),
    )

    if match is None:
        return None

    return int(match.group(1))


# ============================================================
# EXTRACTION DU NOM
# ============================================================

def extract_name(
    tags: dict[str, Any],
) -> str:
    """
    Trouver le nom le plus approprié pour l'hôtel.
    """

    name = (
        tags.get("name")
        or tags.get("name:fr")
        or tags.get("name:en")
        or tags.get("brand")
    )

    if not name:
        return "Hôtel sans nom"

    return str(name)


# ============================================================
# NORMALISATION DES DONNÉES
# ============================================================

def normalize_hotels(
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Nettoyer les résultats OpenStreetMap et les transformer
    en objets compatibles avec Neo4j.
    """

    hotels: list[dict[str, Any]] = []

    identifiers_seen: set[str] = set()

    for element in elements:
        latitude, longitude = extract_coordinates(
            element
        )

        if latitude is None or longitude is None:
            continue

        try:
            latitude = float(latitude)
            longitude = float(longitude)

        except (TypeError, ValueError):
            continue

        if not -90 <= latitude <= 90:
            continue

        if not -180 <= longitude <= 180:
            continue

        osm_type = str(
            element.get(
                "type",
                "unknown",
            )
        )

        osm_identifier = element.get("id")

        if osm_identifier is None:
            continue

        hotel_identifier = (
            f"osm-{osm_type}-{osm_identifier}"
        )

        if hotel_identifier in identifiers_seen:
            continue

        identifiers_seen.add(
            hotel_identifier
        )

        tags = element.get("tags", {})

        if not isinstance(tags, dict):
            tags = {}

        city = (
            tags.get("addr:city")
            or tags.get("addr:town")
            or "Casablanca"
        )

        hotel = {
            "id": hotel_identifier,
            "osm_id": str(osm_identifier),
            "osm_type": osm_type,
            "name": extract_name(tags),
            "address": build_address(tags),
            "stars": extract_stars(tags),
            "phone": (
                tags.get("phone")
                or tags.get("contact:phone")
                or tags.get("mobile")
            ),
            "email": (
                tags.get("email")
                or tags.get("contact:email")
            ),
            "website": (
                tags.get("website")
                or tags.get("contact:website")
            ),
            "city": str(city),
            "latitude": latitude,
            "longitude": longitude,
            "source": "OpenStreetMap",
        }

        hotels.append(hotel)

    print()
    print(
        f"{len(hotels)} hôtel(s) valide(s) "
        "après le nettoyage."
    )

    return hotels


# ============================================================
# CRÉATION DES CONTRAINTES ET INDEX
# ============================================================

def create_database_schema() -> None:
    """
    Créer la contrainte d'unicité et l'index géographique.
    """

    driver.execute_query(
        """
        CREATE CONSTRAINT hotel_id_unique IF NOT EXISTS
        FOR (hotel:Hotel)
        REQUIRE hotel.id IS UNIQUE
        """,
        database_="neo4j",
    )

    driver.execute_query(
        """
        CREATE POINT INDEX hotel_location_index IF NOT EXISTS
        FOR (hotel:Hotel)
        ON (hotel.location)
        """,
        database_="neo4j",
    )

    driver.execute_query(
        """
        CREATE CONSTRAINT city_name_unique IF NOT EXISTS
        FOR (city:City)
        REQUIRE city.name IS UNIQUE
        """,
        database_="neo4j",
    )

    print(
        "Contraintes et index Neo4j vérifiés."
    )


# ============================================================
# INSERTION D'UN LOT D'HÔTELS
# ============================================================

def insert_hotel_batch(
    hotels_batch: list[dict[str, Any]],
) -> None:
    """
    Insérer un lot d'hôtels dans Neo4j.
    """

    query = """
    UNWIND $hotels AS hotel

    MERGE (h:Hotel {id: hotel.id})

    SET
        h.osm_id = hotel.osm_id,
        h.osm_type = hotel.osm_type,
        h.name = hotel.name,
        h.address = hotel.address,
        h.stars = hotel.stars,
        h.phone = hotel.phone,
        h.email = hotel.email,
        h.website = hotel.website,
        h.source = hotel.source,
        h.location = point({
            latitude: hotel.latitude,
            longitude: hotel.longitude
        }),
        h.updated_at = datetime()

    MERGE (city:City {name: hotel.city})

    MERGE (h)-[:LOCATED_IN]->(city)
    """

    driver.execute_query(
        query,
        hotels=hotels_batch,
        database_="neo4j",
    )


# ============================================================
# INSERTION DE TOUS LES HÔTELS
# ============================================================

def insert_hotels(
    hotels: list[dict[str, Any]],
) -> None:
    """
    Insérer les hôtels par lots pour éviter une requête
    Neo4j trop volumineuse.
    """

    if not hotels:
        print(
            "Aucun hôtel à insérer."
        )
        return

    total_hotels = len(hotels)

    print()
    print(
        f"Importation de {total_hotels} hôtel(s) "
        "dans Neo4j..."
    )

    inserted_count = 0

    for start_index in range(
        0,
        total_hotels,
        BATCH_SIZE,
    ):
        end_index = start_index + BATCH_SIZE

        hotels_batch = hotels[
            start_index:end_index
        ]

        insert_hotel_batch(
            hotels_batch
        )

        inserted_count += len(
            hotels_batch
        )

        print(
            f"Progression : "
            f"{inserted_count}/{total_hotels}"
        )

    print(
        f"{inserted_count} hôtel(s) importé(s) "
        "ou mis à jour."
    )


# ============================================================
# VÉRIFICATION DE L'IMPORTATION
# ============================================================

def verify_import() -> None:
    """
    Afficher un résumé des hôtels présents dans Neo4j.
    """

    records, _, _ = driver.execute_query(
        """
        MATCH (hotel:Hotel)

        RETURN
            count(hotel) AS total_hotels,

            coalesce(
                sum(
                    CASE
                        WHEN hotel.source = "OpenStreetMap"
                        THEN 1
                        ELSE 0
                    END
                ),
                0
            ) AS osm_hotels
        """,
        database_="neo4j",
    )

    result = records[0]

    print()
    print("=" * 65)
    print("RÉSUMÉ DE LA BASE NEO4J")
    print("=" * 65)

    print(
        f"Nombre total d'hôtels : "
        f"{result['total_hotels']}"
    )

    print(
        f"Hôtels OpenStreetMap : "
        f"{result['osm_hotels']}"
    )


# ============================================================
# AFFICHER QUELQUES HÔTELS
# ============================================================

def display_sample() -> None:
    """
    Afficher quelques hôtels importés pour vérifier les données.
    """

    records, _, _ = driver.execute_query(
        """
        MATCH (hotel:Hotel)

        WHERE hotel.source = "OpenStreetMap"

        RETURN
            hotel.name AS name,
            hotel.address AS address,
            hotel.stars AS stars,
            hotel.location.latitude AS latitude,
            hotel.location.longitude AS longitude

        ORDER BY hotel.name

        LIMIT 10
        """,
        database_="neo4j",
    )

    if not records:
        return

    print()
    print("Exemples d'hôtels importés :")

    for record in records:
        stars = (
            record["stars"]
            if record["stars"] is not None
            else "non renseigné"
        )

        print(
            f"- {record['name']} | "
            f"étoiles : {stars} | "
            f"{record['latitude']}, "
            f"{record['longitude']}"
        )


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main() -> None:
    """
    Exécuter toutes les étapes de l'importation.
    """

    try:
        print(
            "Vérification de la connexion à Neo4j..."
        )

        driver.verify_connectivity()

        print(
            "Connexion à Neo4j réussie."
        )

        create_database_schema()

        elements = fetch_osm_hotels()

        hotels = normalize_hotels(
            elements
        )

        insert_hotels(
            hotels
        )

        verify_import()

        display_sample()

        print()
        print(
            "Importation terminée avec succès."
        )

    except Exception as error:
        print()
        print("=" * 65)
        print("ÉCHEC DE L'IMPORTATION")
        print("=" * 65)

        print(
            f"Erreur : {error}"
        )

    finally:
        driver.close()

        print(
            "Connexion Neo4j fermée."
        )


if __name__ == "__main__":
    main()