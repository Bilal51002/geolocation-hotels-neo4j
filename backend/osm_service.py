import re
import time
from typing import Any

import requests


OVERPASS_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

MAX_ATTEMPTS_PER_SERVER = 2
MAX_IMPORT_RADIUS = 20000


def build_overpass_query(
    latitude: float,
    longitude: float,
    radius: int,
) -> str:
    """
    Construire une requête Overpass autour d'une position.
    """

    safe_radius = min(
        max(int(radius), 500),
        MAX_IMPORT_RADIUS,
    )

    return f"""
    [out:json][timeout:120];

    (
        node["tourism"="hotel"]
            (around:{safe_radius},{latitude},{longitude});

        way["tourism"="hotel"]
            (around:{safe_radius},{latitude},{longitude});

        relation["tourism"="hotel"]
            (around:{safe_radius},{latitude},{longitude});
    );

    out center tags;
    """


def fetch_hotels_from_osm(
    latitude: float,
    longitude: float,
    radius: int,
) -> list[dict[str, Any]]:
    """
    Télécharger les hôtels autour d'une position.
    """

    query = build_overpass_query(
        latitude,
        longitude,
        radius,
    )

    headers = {
        "User-Agent": (
            "geolocation-project/1.0 "
            "(educational project)"
        ),
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    with requests.Session() as session:
        session.headers.update(headers)

        for server_url in OVERPASS_URLS:
            for attempt in range(
                1,
                MAX_ATTEMPTS_PER_SERVER + 1,
            ):
                try:
                    print(
                        f"Overpass : {server_url} "
                        f"tentative {attempt}"
                    )

                    response = session.post(
                        server_url,
                        data={"data": query},
                        timeout=(20, 150),
                    )

                    response.raise_for_status()

                    data = response.json()

                    return data.get("elements", [])

                except (
                    requests.Timeout,
                    requests.ConnectionError,
                    requests.HTTPError,
                    ValueError,
                ) as error:
                    last_error = error

                    print(
                        "Erreur Overpass :",
                        error,
                    )

                    if attempt < MAX_ATTEMPTS_PER_SERVER:
                        time.sleep(5)

    raise RuntimeError(
        "Aucun serveur Overpass n'a répondu. "
        f"Dernière erreur : {last_error}"
    )


def extract_coordinates(
    element: dict[str, Any],
) -> tuple[float | None, float | None]:
    """
    Extraire les coordonnées d'un node, way ou relation.
    """

    if element.get("type") == "node":
        return (
            element.get("lat"),
            element.get("lon"),
        )

    center = element.get("center", {})

    return (
        center.get("lat"),
        center.get("lon"),
    )


def build_address(
    tags: dict[str, Any],
) -> str:
    """
    Construire une adresse à partir des tags OSM.
    """

    parts = []

    for key in [
        "addr:housenumber",
        "addr:street",
        "addr:neighbourhood",
        "addr:suburb",
        "addr:postcode",
        "addr:city",
    ]:
        value = tags.get(key)

        if value:
            parts.append(str(value))

    return (
        ", ".join(parts)
        if parts
        else "Adresse non disponible"
    )


def extract_stars(
    tags: dict[str, Any],
) -> int | None:
    """
    Extraire le nombre d'étoiles.
    """

    raw_value = (
        tags.get("stars")
        or tags.get("hotel:stars")
    )

    if raw_value is None:
        return None

    match = re.search(
        r"[1-5]",
        str(raw_value),
    )

    if match is None:
        return None

    return int(match.group())


def normalize_hotels(
    elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Nettoyer les résultats OpenStreetMap.
    """

    hotels = []
    identifiers = set()

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

        osm_id = element.get("id")
        osm_type = element.get("type")

        if osm_id is None or osm_type is None:
            continue

        identifier = f"osm-{osm_type}-{osm_id}"

        if identifier in identifiers:
            continue

        identifiers.add(identifier)

        tags = element.get("tags", {})

        if not isinstance(tags, dict):
            tags = {}

        name = (
            tags.get("name")
            or tags.get("name:fr")
            or tags.get("name:en")
            or tags.get("brand")
            or "Hôtel sans nom"
        )

        city = (
            tags.get("addr:city")
            or tags.get("addr:town")
            or tags.get("addr:village")
            or "Ville non renseignée"
        )

        hotels.append(
            {
                "id": identifier,
                "osm_id": str(osm_id),
                "osm_type": str(osm_type),
                "name": str(name),
                "address": build_address(tags),
                "stars": extract_stars(tags),
                "phone": (
                    tags.get("phone")
                    or tags.get("contact:phone")
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
        )

    return hotels


def insert_hotels_in_neo4j(
    driver,
    hotels: list[dict[str, Any]],
) -> int:
    """
    Insérer les hôtels dans Neo4j.
    """

    if not hotels:
        return 0

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
        hotels=hotels,
        database_="neo4j",
    )

    return len(hotels)


def import_hotels_nearby(
    driver,
    latitude: float,
    longitude: float,
    radius: int,
) -> int:
    """
    Télécharger puis importer les hôtels d'une zone.
    """

    elements = fetch_hotels_from_osm(
        latitude,
        longitude,
        radius,
    )

    hotels = normalize_hotels(elements)

    return insert_hotels_in_neo4j(
        driver,
        hotels,
    )