import atexit
import math
import os
import time
from osm_service import import_hotels_nearby

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from neo4j import GraphDatabase


# ============================================================
# INITIALISATION DE FLASK
# ============================================================

app = Flask(__name__)
CORS(app)


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
        "La variable d'environnement NEO4J_PASSWORD "
        "n'est pas définie."
    )


driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(
        NEO4J_USER,
        NEO4J_PASSWORD,
    ),
)


# ============================================================
# ATTENDRE LE DÉMARRAGE DE NEO4J
# ============================================================

def wait_for_neo4j(
    attempts: int = 30,
    delay: int = 2,
) -> None:
    """
    Attendre que Neo4j soit complètement disponible.

    Le backend effectue plusieurs tentatives, car le conteneur
    Neo4j peut prendre plus de temps à démarrer que Flask.
    """

    for attempt in range(1, attempts + 1):
        try:
            driver.verify_connectivity()

            print("Connexion à Neo4j réussie.")
            return

        except Exception as error:
            print(
                f"Attente de Neo4j "
                f"({attempt}/{attempts}) : {error}"
            )

            time.sleep(delay)

    raise RuntimeError(
        "Impossible de se connecter à Neo4j "
        "après plusieurs tentatives."
    )


# ============================================================
# FERMETURE DU DRIVER NEO4J
# ============================================================

@atexit.register
def close_neo4j_driver() -> None:
    """
    Fermer proprement la connexion Neo4j
    lorsque l'application s'arrête.
    """

    driver.close()


# ============================================================
# ROUTE D'ACCUEIL
# ============================================================

@app.get("/")
def home():
    """
    Route principale de l'API.
    """

    return jsonify(
        {
            "message": "API du projet de géolocalisation",
            "status": "running",
        }
    )


# ============================================================
# ROUTE DE VÉRIFICATION
# ============================================================

@app.get("/api/health")
def health():
    """
    Vérifier que Flask et Neo4j fonctionnent correctement.
    """

    try:
        records, _, _ = driver.execute_query(
            """
            RETURN
                'connected' AS neo4j_status,
                datetime() AS server_date
            """,
            database_="neo4j",
        )

        result = records[0]

        return jsonify(
            {
                "backend": "connected",
                "neo4j": result["neo4j_status"],
                "server_date": str(result["server_date"]),
            }
        )

    except Exception as error:
        return jsonify(
            {
                "backend": "connected",
                "neo4j": "disconnected",
                "error": str(error),
            }
        ), 503


# ============================================================
# ROUTE DE RECHERCHE DES HÔTELS À PROXIMITÉ
# ============================================================

@app.get("/api/hotels/nearby")
def nearby_hotels():
    """
    Rechercher les hôtels proches d'une position géographique.

    Paramètres attendus dans l'URL :

    lat :
        latitude de l'utilisateur.

    lon :
        longitude de l'utilisateur.

    radius :
        rayon maximal en mètres.
        Ce paramètre est facultatif.
        Sa valeur par défaut est 5000 mètres.

    Exemple :

    /api/hotels/nearby
        ?lat=33.5731
        &lon=-7.5898
        &radius=5000
    """

    # --------------------------------------------------------
    # RÉCUPÉRER ET CONVERTIR LES PARAMÈTRES
    # --------------------------------------------------------

    try:
        latitude = float(request.args["lat"])
        longitude = float(request.args["lon"])

        radius = float(
            request.args.get(
                "radius",
                5000,
            )
        )

    except KeyError:
        return jsonify(
            {
                "error": (
                    "Les paramètres 'lat' et 'lon' "
                    "sont obligatoires."
                )
            }
        ), 400

    except ValueError:
        return jsonify(
            {
                "error": (
                    "Les paramètres 'lat', 'lon' et 'radius' "
                    "doivent contenir des nombres valides."
                )
            }
        ), 400

    # --------------------------------------------------------
    # VÉRIFIER QUE LES VALEURS SONT FINIES
    # --------------------------------------------------------

    if not all(
        math.isfinite(value)
        for value in [
            latitude,
            longitude,
            radius,
        ]
    ):
        return jsonify(
            {
                "error": (
                    "Les paramètres ne peuvent pas contenir "
                    "NaN ou une valeur infinie."
                )
            }
        ), 400

    # --------------------------------------------------------
    # VALIDER LA LATITUDE
    # --------------------------------------------------------

    if latitude < -90 or latitude > 90:
        return jsonify(
            {
                "error": (
                    "La latitude doit être comprise "
                    "entre -90 et 90."
                )
            }
        ), 400

    # --------------------------------------------------------
    # VALIDER LA LONGITUDE
    # --------------------------------------------------------

    if longitude < -180 or longitude > 180:
        return jsonify(
            {
                "error": (
                    "La longitude doit être comprise "
                    "entre -180 et 180."
                )
            }
        ), 400

    # --------------------------------------------------------
    # VALIDER LE RAYON
    # --------------------------------------------------------

    if radius <= 0 or radius > 50000:
        return jsonify(
            {
                "error": (
                    "Le rayon doit être compris "
                    "entre 1 et 50000 mètres."
                )
            }
        ), 400

    # --------------------------------------------------------
    # REQUÊTE CYPHER
    # --------------------------------------------------------

    query = """
    WITH point({
        latitude: $latitude,
        longitude: $longitude
    }) AS user_location

    MATCH (hotel:Hotel)

    WHERE hotel.location IS NOT NULL

    WITH
        hotel,
        point.distance(
            user_location,
            hotel.location
        ) AS distance

    WHERE distance <= $radius

    RETURN
        hotel.id AS id,
        hotel.name AS name,
        hotel.address AS address,
        hotel.stars AS stars,
        hotel.location.latitude AS latitude,
        hotel.location.longitude AS longitude,
        round(distance) AS distance_metres

    ORDER BY distance ASC

    LIMIT 100
    """

    # --------------------------------------------------------
    # EXÉCUTER LA REQUÊTE
    # --------------------------------------------------------

    try:
        records, _, _ = driver.execute_query(
            query,
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            database_="neo4j",
        )

        hotels = []

        for record in records:
            hotels.append(
                {
                    "id": record["id"],
                    "name": record["name"],
                    "address": record["address"],
                    "stars": record["stars"],
                    "latitude": record["latitude"],
                    "longitude": record["longitude"],
                    "distance_metres": record[
                        "distance_metres"
                    ],
                }
            )

        return jsonify(
            {
                "reference": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_metres": radius,
                },
                "count": len(hotels),
                "hotels": hotels,
            }
        )

    except Exception as error:
        print(
            "Erreur pendant la recherche des hôtels :",
            error,
        )

        return jsonify(
            {
                "error": (
                    "Une erreur est survenue pendant "
                    "la recherche des hôtels."
                ),
                "details": str(error),
            }
        ), 500


# ============================================================
# ROUTE D'ITINÉRAIRE RÉEL (PROXY OSRM)
# ============================================================

OSRM_BASE_URL = os.getenv(
    "OSRM_BASE_URL",
    "https://router.project-osrm.org",
)

OSRM_PROFILES = {
    "foot": "foot",
    "walking": "foot",
    "car": "driving",
    "driving": "driving",
    "bike": "bike",
    "cycling": "bike",
}


@app.get("/api/route")
def get_route():
    """
    Calculer un itinéraire routier réel entre deux points
    en s'appuyant sur un serveur OSRM public.

    Paramètres attendus dans l'URL :

    start_lat, start_lon :
        position de départ (l'utilisateur).

    end_lat, end_lon :
        position d'arrivée (l'hôtel).

    profile :
        mode de déplacement : "foot", "car" ou "bike".
        Valeur par défaut : "car".

    Exemple :

    /api/route
        ?start_lat=34.0331&start_lon=-5.0003
        &end_lat=34.0450&end_lon=-4.9800
        &profile=car
    """

    try:
        start_lat = float(request.args["start_lat"])
        start_lon = float(request.args["start_lon"])
        end_lat = float(request.args["end_lat"])
        end_lon = float(request.args["end_lon"])

    except (KeyError, ValueError):
        return jsonify(
            {
                "error": (
                    "Les paramètres start_lat, start_lon, "
                    "end_lat et end_lon sont obligatoires "
                    "et doivent être des nombres valides."
                )
            }
        ), 400

    profile_key = request.args.get("profile", "car")
    osrm_profile = OSRM_PROFILES.get(profile_key)

    if osrm_profile is None:
        return jsonify(
            {
                "error": (
                    "Le paramètre 'profile' doit valoir "
                    "'foot', 'car' ou 'bike'."
                )
            }
        ), 400

    # OSRM attend les coordonnées au format longitude,latitude
    coordinates = (
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
    )

    url = (
        f"{OSRM_BASE_URL}/route/v1/{osrm_profile}/"
        f"{coordinates}"
    )

    try:
        response = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
            },
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return jsonify(
                {
                    "error": (
                        "Aucun itinéraire trouvé entre "
                        "ces deux points."
                    )
                }
            ), 404

        route = data["routes"][0]

        return jsonify(
            {
                "profile": profile_key,
                "distance_metres": round(route["distance"]),
                "duration_seconds": round(route["duration"]),
                "geometry": route["geometry"],
            }
        )

    except requests.RequestException as error:
        print("Erreur pendant l'appel à OSRM :", error)

        return jsonify(
            {
                "error": (
                    "Le service de calcul d'itinéraire est "
                    "actuellement indisponible."
                ),
                "details": str(error),
            }
        ), 502


# ============================================================
# ROUTE DE STATISTIQUES POUR LE DASHBOARD
# ============================================================

@app.get("/api/dashboard/stats")
def dashboard_stats():
    """
    Calculer des statistiques globales sur les hôtels stockés
    dans Neo4j, utilisées par le tableau de bord du frontend.
    """

    try:
        # ----------------------------------------------------
        # COMPTEURS GLOBAUX
        # ----------------------------------------------------

        summary_query = """
        MATCH (h:Hotel)

        RETURN
            count(h) AS total,

            count(
                CASE WHEN h.stars IS NOT NULL
                THEN 1 END
            ) AS with_stars,

            count(
                CASE WHEN h.phone IS NOT NULL
                THEN 1 END
            ) AS with_phone,

            count(
                CASE WHEN h.address IS NOT NULL
                    AND h.address <> 'Adresse non disponible'
                THEN 1 END
            ) AS with_address,

            avg(h.location.latitude) AS centre_latitude,
            avg(h.location.longitude) AS centre_longitude
        """

        summary_records, _, _ = driver.execute_query(
            summary_query,
            database_="neo4j",
        )

        summary = summary_records[0]
        total = summary["total"]

        # ----------------------------------------------------
        # RÉPARTITION PAR ZONE (QUARTIERS DE FÈS)
        # ----------------------------------------------------
        #
        # Les données OSM stockent des noms de ville très
        # hétérogènes (variantes de casse, accents, arabe /
        # latin, valeurs manquantes). Plutôt que de regrouper
        # par h.city, on classe chaque hôtel dans le quartier
        # de Fès dont il est géographiquement le plus proche,
        # comme dans le tableau de bord de référence.
        #
        # NOTE : ces coordonnées sont spécifiques à Fès.
        # Pour une autre ville, il faudrait adapter les points
        # de référence ci-dessous.

        zones_query = """
        WITH
            point({latitude: 34.0625, longitude: -4.9770})
                AS fes_el_bali,
            point({latitude: 34.0580, longitude: -5.0010})
                AS fes_el_jdid,
            point({latitude: 34.0400, longitude: -4.9850})
                AS ville_nouvelle

        MATCH (h:Hotel)

        WITH
            h,
            point.distance(h.location, fes_el_bali)
                AS distance_medina,
            point.distance(h.location, fes_el_jdid)
                AS distance_jdid,
            point.distance(h.location, ville_nouvelle)
                AS distance_nouvelle

        WITH
            h,
            CASE
                WHEN distance_medina <= distance_jdid
                    AND distance_medina <= distance_nouvelle
                    THEN distance_medina
                WHEN distance_jdid <= distance_medina
                    AND distance_jdid <= distance_nouvelle
                    THEN distance_jdid
                ELSE distance_nouvelle
            END AS closest_distance,
            CASE
                WHEN distance_medina <= distance_jdid
                    AND distance_medina <= distance_nouvelle
                    THEN 'Fès el-Bali'
                WHEN distance_jdid <= distance_medina
                    AND distance_jdid <= distance_nouvelle
                    THEN 'Fès el-Jdid'
                ELSE 'Ville Nouvelle'
            END AS closest_zone

        WITH
            CASE
                WHEN closest_distance > 4000 THEN 'Périphérie'
                ELSE closest_zone
            END AS zone

        RETURN zone, count(*) AS count
        ORDER BY count DESC
        """

        zones_records, _, _ = driver.execute_query(
            zones_query,
            database_="neo4j",
        )

        zones = [
            {
                "zone": record["zone"],
                "count": record["count"],
            }
            for record in zones_records
        ]

        # ----------------------------------------------------
        # RÉPARTITION PAR ÉTOILES
        # ----------------------------------------------------

        stars_query = """
        MATCH (h:Hotel)
        WHERE h.stars IS NOT NULL
        RETURN h.stars AS stars, count(h) AS count
        ORDER BY stars ASC
        """

        stars_records, _, _ = driver.execute_query(
            stars_query,
            database_="neo4j",
        )

        by_stars = [
            {
                "stars": record["stars"],
                "count": record["count"],
            }
            for record in stars_records
        ]

        # ----------------------------------------------------
        # DISTRIBUTION PAR DISTANCE AU CENTRE
        # ----------------------------------------------------

        distance_bands = {
            "0-1 km": 0,
            "1-2 km": 0,
            "2-3 km": 0,
            "3-5 km": 0,
            "5+ km": 0,
        }

        centre_latitude = summary["centre_latitude"]
        centre_longitude = summary["centre_longitude"]

        if (
            total > 0
            and centre_latitude is not None
            and centre_longitude is not None
        ):
            distances_query = """
            WITH point({
                latitude: $latitude,
                longitude: $longitude
            }) AS centre

            MATCH (h:Hotel)

            RETURN
                point.distance(centre, h.location) / 1000.0
                AS distance_km
            """

            distances_records, _, _ = driver.execute_query(
                distances_query,
                latitude=centre_latitude,
                longitude=centre_longitude,
                database_="neo4j",
            )

            for record in distances_records:
                distance_km = record["distance_km"]

                if distance_km < 1:
                    distance_bands["0-1 km"] += 1
                elif distance_km < 2:
                    distance_bands["1-2 km"] += 1
                elif distance_km < 3:
                    distance_bands["2-3 km"] += 1
                elif distance_km < 5:
                    distance_bands["3-5 km"] += 1
                else:
                    distance_bands["5+ km"] += 1

        # ----------------------------------------------------
        # MEILLEURS HÔTELS (LES MIEUX NOTÉS)
        # ----------------------------------------------------

        top_hotels_query = """
        MATCH (h:Hotel)
        WHERE h.stars IS NOT NULL
        RETURN
            h.name AS name,
            h.stars AS stars,
            h.address AS address
        ORDER BY h.stars DESC, h.name ASC
        LIMIT 6
        """

        top_hotels_records, _, _ = driver.execute_query(
            top_hotels_query,
            database_="neo4j",
        )

        top_hotels = [
            {
                "name": record["name"],
                "stars": record["stars"],
                "address": record["address"],
            }
            for record in top_hotels_records
        ]

        return jsonify(
            {
                "total": total,
                "with_stars": summary["with_stars"],
                "with_phone": summary["with_phone"],
                "with_address": summary["with_address"],
                "zones": zones,
                "by_stars": by_stars,
                "distance_distribution": [
                    {"band": band, "count": count}
                    for band, count in distance_bands.items()
                ],
                "top_hotels": top_hotels,
            }
        )

    except Exception as error:
        print(
            "Erreur pendant le calcul des statistiques :",
            error,
        )

        return jsonify(
            {
                "error": (
                    "Impossible de calculer les statistiques "
                    "du tableau de bord."
                ),
                "details": str(error),
            }
        ), 500


# ============================================================
# GESTION DES ROUTES INEXISTANTES
# ============================================================

@app.errorhandler(404)
def route_not_found(error):
    """
    Retourner une réponse JSON lorsqu'une route n'existe pas.
    """

    return jsonify(
        {
            "error": "Route introuvable.",
            "available_routes": [
                "/",
                "/api/health",
                "/api/hotels/nearby",
                "/api/route",
                "/api/dashboard/stats",
            ],
        }
    ), 404


@app.post("/api/hotels/import-nearby")
def import_nearby_hotels():
    """
    Télécharger et enregistrer dans Neo4j les hôtels situés
    autour d'une position géographique.

    Corps JSON attendu :

    {
        "lat": 34.0331,
        "lon": -5.0003,
        "radius": 20000
    }
    """

    payload = request.get_json(silent=True)

    if payload is None:
        payload = {}

    try:
        latitude = float(
            payload.get(
                "lat",
                request.args.get("lat"),
            )
        )

        longitude = float(
            payload.get(
                "lon",
                request.args.get("lon"),
            )
        )

        radius = float(
            payload.get(
                "radius",
                request.args.get("radius", 10000),
            )
        )

    except (TypeError, ValueError):
        return jsonify(
            {
                "error": (
                    "Les paramètres lat, lon et radius "
                    "doivent être des nombres valides."
                )
            }
        ), 400

    if not all(
        math.isfinite(value)
        for value in [
            latitude,
            longitude,
            radius,
        ]
    ):
        return jsonify(
            {
                "error": (
                    "Les paramètres ne doivent pas contenir "
                    "NaN ou une valeur infinie."
                )
            }
        ), 400

    if latitude < -90 or latitude > 90:
        return jsonify(
            {
                "error": (
                    "La latitude doit être comprise "
                    "entre -90 et 90."
                )
            }
        ), 400

    if longitude < -180 or longitude > 180:
        return jsonify(
            {
                "error": (
                    "La longitude doit être comprise "
                    "entre -180 et 180."
                )
            }
        ), 400

    if radius <= 0 or radius > 20000:
        return jsonify(
            {
                "error": (
                    "Le rayon d'importation doit être compris "
                    "entre 1 et 20000 mètres."
                )
            }
        ), 400

    try:
        print(
            "Importation dynamique autour de : "
            f"{latitude}, {longitude}, rayon {radius} mètres."
        )

        imported_count = import_hotels_nearby(
            driver=driver,
            latitude=latitude,
            longitude=longitude,
            radius=int(radius),
        )

        return jsonify(
            {
                "message": (
                    "Importation OpenStreetMap terminée."
                ),
                "imported_count": imported_count,
                "reference": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius_metres": radius,
                },
            }
        )

    except Exception as error:
        print(
            "Erreur pendant l'importation dynamique :",
            error,
        )

        return jsonify(
            {
                "error": (
                    "Impossible d'importer les hôtels "
                    "depuis OpenStreetMap."
                ),
                "details": str(error),
            }
        ), 502


# ============================================================
# DÉMARRAGE DE L'APPLICATION
# ============================================================

if __name__ == "__main__":
    wait_for_neo4j()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )