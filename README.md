# Hotel Finder — Recherche géographique d'hôtels

Application web full-stack permettant de rechercher les hôtels situés
autour d'une position donnée, d'obtenir un itinéraire réel jusqu'à
chacun d'eux, et de consulter un tableau de bord statistique.

Les hôtels sont récupérés depuis OpenStreetMap, stockés dans Neo4j
et classés du plus proche au plus éloigné grâce aux fonctions
géospatiales natives de Neo4j (type `POINT`, `point.distance()`).

## Fonctionnalités

- Recherche par proximité (latitude/longitude ou clic sur la carte)
- Rayon de recherche réglable de 1 à 20 km (slider)
- Récupération de la position GPS de l'utilisateur
- Importation automatique des hôtels manquants depuis OpenStreetMap
- Calcul d'itinéraires réels (à pied, en voiture, à vélo) via OSRM,
  avec distance et durée estimée
- Tableau de bord : nombre d'hôtels, taux de complétude des données,
  répartition par quartier de Fès, distribution par distance,
  classement par étoiles
- Conteneurisation complète avec Docker Compose

## Technologies utilisées

- **Frontend** : React, Vite, React Router, React-Leaflet, Recharts, Axios
- **Backend** : Python 3.11, Flask, driver Neo4j
- **Base de données** : Neo4j (Graph Database, type géospatial `POINT`)
- **Données géographiques** : OpenStreetMap et Overpass API
- **Itinéraires** : OSRM (Open Source Routing Machine)
- **Infrastructure** : Docker, Docker Compose, Nginx

## Architecture

Le projet contient trois conteneurs :

- `frontend` : application React (Vite) compilée puis servie par Nginx,
  qui fait également office de reverse proxy vers `/api`
- `backend` : API REST Flask (recherche, import OSM, proxy OSRM,
  statistiques) connectée à Neo4j via son driver officiel
- `neo4j` : base de données géospatiale stockant les hôtels

## Installation

### 1. Cloner le dépôt

```bash
git clone URL_DU_DEPOT
cd geolocation-project
```

### 2. Configurer les variables d'environnement

Copier `.env.example` en `.env` et renseigner un mot de passe Neo4j :

```bash
cp .env.example .env
```

### 3. Lancer l'application

```bash
docker compose up --build
```

- Frontend : http://localhost:8080
- Backend (API) : http://localhost:5000
- Neo4j Browser : http://localhost:7474
