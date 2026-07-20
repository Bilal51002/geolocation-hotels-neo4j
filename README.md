# Projet de recherche géographique d'hôtels

Application web permettant de rechercher les hôtels situés autour de la position actuelle de l'utilisateur.

Les hôtels sont récupérés depuis OpenStreetMap, stockés dans Neo4j et classés du plus proche au plus éloigné.

## Technologies utilisées

- Docker et Docker Compose
- Python 3.11
- Flask
- Neo4j
- OpenStreetMap et Overpass API
- HTML, CSS et JavaScript
- Leaflet
- Nginx

## Architecture

Le projet contient trois conteneurs :

- `frontend` : Nginx, HTML, CSS, JavaScript et Leaflet
- `backend` : Flask et driver Neo4j
- `neo4j` : base de données géographique

## Fonctionnalités

- Récupération de la position actuelle
- Choix du rayon de recherche
- Recherche des hôtels autour de l'utilisateur
- Importation automatique depuis OpenStreetMap
- Stockage géographique avec le type `POINT` de Neo4j
- Calcul de la distance entre l'utilisateur et les hôtels
- Classement du plus proche au plus éloigné
- Affichage des résultats sur une carte interactive
- Conteneurisation complète avec Docker

## Installation

### 1. Cloner le dépôt

```bash
git clone URL_DU_DEPOT
cd geolocation-project