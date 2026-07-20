import atexit
import math
import os
import time
from osm_service import import_hotels_nearby

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