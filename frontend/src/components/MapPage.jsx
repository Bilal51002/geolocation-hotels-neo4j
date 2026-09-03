import { useCallback, useEffect, useRef, useState } from "react";
import {
    Circle,
    MapContainer,
    Marker,
    Polyline,
    Popup,
    TileLayer,
} from "react-leaflet";
import L from "leaflet";

import "../leafletIconFix.js";
import {
    fetchNearbyHotels,
    fetchRoute,
    importNearbyHotels,
} from "../api.js";
import { formatDistance, formatDuration, starsLabel } from "../format.js";
import FitBounds from "./FitBounds.jsx";
import MapClickHandler from "./MapClickHandler.jsx";

const DEFAULT_POSITION = {
    latitude: 34.0331,
    longitude: -5.0003,
};

const TRAVEL_MODES = [
    { profile: "foot", icon: "🚶", label: "À pied" },
    { profile: "car", icon: "🚗", label: "Voiture" },
    { profile: "bike", icon: "🚲", label: "Vélo" },
];

const referenceIcon = L.divIcon({
    className: "",
    html:
        '<div style="' +
        "width:16px;height:16px;border-radius:50%;" +
        "background:#2563eb;border:3px solid white;" +
        'box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
});

export default function MapPage() {
    const [latitude, setLatitude] = useState(DEFAULT_POSITION.latitude);
    const [longitude, setLongitude] = useState(DEFAULT_POSITION.longitude);
    const [radiusKm, setRadiusKm] = useState(5);

    const [reference, setReference] = useState(null);
    const [hotels, setHotels] = useState([]);
    const [selectedHotel, setSelectedHotel] = useState(null);
    const [selectedProfile, setSelectedProfile] = useState("foot");
    const [route, setRoute] = useState(null);

    const [status, setStatus] = useState({
        message:
            "Astuce : cliquez sur la carte pour choisir un point " +
            "de référence.",
        type: "",
    });

    const [isLoading, setIsLoading] = useState(false);

    const requestIdRef = useRef(0);

    /* ========================================================
       RECHERCHE PRINCIPALE
       ======================================================== */

    const searchHotels = useCallback(
        async (searchLatitude, searchLongitude, searchRadiusKm) => {
            const currentRequestId = ++requestIdRef.current;
            const radiusMetres = searchRadiusKm * 1000;

            setReference({
                latitude: searchLatitude,
                longitude: searchLongitude,
            });

            setSelectedHotel(null);
            setRoute(null);
            setIsLoading(true);

            setStatus({
                message: "Recherche des hôtels dans la base Neo4j...",
                type: "loading",
            });

            try {
                let searchData = await fetchNearbyHotels(
                    searchLatitude,
                    searchLongitude,
                    radiusMetres,
                );

                if (searchData.count === 0) {
                    setStatus({
                        message:
                            "Aucun hôtel en base pour cette zone. " +
                            "Importation depuis OpenStreetMap...",
                        type: "loading",
                    });

                    const importData = await importNearbyHotels(
                        searchLatitude,
                        searchLongitude,
                        radiusMetres,
                    );

                    setStatus({
                        message:
                            `${importData.imported_count} hôtel(s) ` +
                            "importé(s). Nouvelle recherche...",
                        type: "loading",
                    });

                    searchData = await fetchNearbyHotels(
                        searchLatitude,
                        searchLongitude,
                        radiusMetres,
                    );
                }

                if (currentRequestId !== requestIdRef.current) {
                    // Une recherche plus récente a déjà été lancée.
                    return;
                }

                setHotels(searchData.hotels);

                if (searchData.count === 0) {
                    setStatus({
                        message:
                            "Aucun hôtel trouvé dans un rayon de " +
                            `${searchRadiusKm} km.`,
                        type: "success",
                    });

                    return;
                }

                setStatus({
                    message:
                        `${searchData.count} hôtel(s) trouvé(s) dans ` +
                        `un rayon de ${searchRadiusKm} km.`,
                    type: "success",
                });

            } catch (error) {
                console.error(error);

                if (currentRequestId !== requestIdRef.current) {
                    return;
                }

                setHotels([]);

                setStatus({
                    message:
                        error?.response?.data?.error ||
                        error.message ||
                        "Erreur pendant la recherche des hôtels.",
                    type: "error",
                });

            } finally {
                if (currentRequestId === requestIdRef.current) {
                    setIsLoading(false);
                }
            }
        },
        [],
    );

    useEffect(() => {
        searchHotels(
            DEFAULT_POSITION.latitude,
            DEFAULT_POSITION.longitude,
            5,
        );
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /* ========================================================
       ITINÉRAIRE VERS L'HÔTEL SÉLECTIONNÉ
       ======================================================== */

    useEffect(() => {
        if (!selectedHotel || !reference) {
            setRoute(null);
            return;
        }

        let cancelled = false;

        async function loadRoute() {
            try {
                const data = await fetchRoute(
                    reference.latitude,
                    reference.longitude,
                    selectedHotel.latitude,
                    selectedHotel.longitude,
                    selectedProfile,
                );

                if (!cancelled) {
                    setRoute(data);
                }

            } catch (error) {
                console.error(error);

                if (!cancelled) {
                    setRoute(null);

                    setStatus({
                        message:
                            "Itinéraire indisponible : " +
                            (error?.response?.data?.error ||
                                error.message),
                        type: "error",
                    });
                }
            }
        }

        loadRoute();

        return () => {
            cancelled = true;
        };
    }, [selectedHotel, selectedProfile, reference]);

    /* ========================================================
       GÉOLOCALISATION
       ======================================================== */

    function useCurrentPosition() {
        if (!navigator.geolocation) {
            setStatus({
                message:
                    "La géolocalisation n'est pas prise en charge " +
                    "par votre navigateur.",
                type: "error",
            });

            return;
        }

        setIsLoading(true);

        setStatus({
            message: "Récupération de votre position...",
            type: "loading",
        });

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const newLatitude = position.coords.latitude;
                const newLongitude = position.coords.longitude;

                setLatitude(newLatitude);
                setLongitude(newLongitude);

                searchHotels(newLatitude, newLongitude, radiusKm);
            },

            (error) => {
                setIsLoading(false);

                let message = "Impossible de récupérer votre position.";

                if (error.code === error.PERMISSION_DENIED) {
                    message =
                        "Vous avez refusé l'accès à votre position.";
                }

                if (error.code === error.POSITION_UNAVAILABLE) {
                    message =
                        "Votre position est actuellement indisponible.";
                }

                if (error.code === error.TIMEOUT) {
                    message =
                        "La récupération de la position a dépassé " +
                        "le délai autorisé.";
                }

                setStatus({ message, type: "error" });
            },

            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 30000,
            },
        );
    }

    /* ========================================================
       CLIC SUR LA CARTE
       ======================================================== */

    function handleMapClick(clickLatitude, clickLongitude) {
        setLatitude(clickLatitude);
        setLongitude(clickLongitude);

        setStatus({
            message:
                "Position sélectionnée sur la carte. " +
                "Cliquez sur Rechercher.",
            type: "",
        });
    }

    /* ========================================================
       POINTS À CADRER SUR LA CARTE
       ======================================================== */

    let fitPoints = [];

    if (reference) {
        fitPoints = [
            [reference.latitude, reference.longitude],
            ...hotels.map((hotel) => [hotel.latitude, hotel.longitude]),
        ];
    }

    if (route) {
        fitPoints = route.geometry.coordinates.map(
            ([lon, lat]) => [lat, lon],
        );
    }

    const routeLatLngs = route
        ? route.geometry.coordinates.map(([lon, lat]) => [lat, lon])
        : null;

    return (
        <main className="page-container">
            <div className="map-layout">
                <aside className="sidebar">
                    <section className="panel card">
                        <h3>🔍 Recherche par proximité</h3>

                        <div className="field">
                            <label htmlFor="latitude">Latitude</label>
                            <input
                                id="latitude"
                                type="number"
                                step="0.0001"
                                value={latitude}
                                onChange={(event) =>
                                    setLatitude(Number(event.target.value))
                                }
                            />
                        </div>

                        <div className="field">
                            <label htmlFor="longitude">Longitude</label>
                            <input
                                id="longitude"
                                type="number"
                                step="0.0001"
                                value={longitude}
                                onChange={(event) =>
                                    setLongitude(Number(event.target.value))
                                }
                            />
                        </div>

                        <div className="field">
                            <div className="slider-row">
                                <label htmlFor="radius">
                                    Rayon de recherche
                                </label>

                                <span className="slider-value">
                                    {radiusKm} km
                                </span>
                            </div>

                            <input
                                id="radius"
                                type="range"
                                min="1"
                                max="20"
                                step="1"
                                value={radiusKm}
                                onChange={(event) =>
                                    setRadiusKm(Number(event.target.value))
                                }
                            />

                            <div className="slider-scale">
                                <span>1 km</span>
                                <span>20 km</span>
                            </div>
                        </div>

                        <button
                            type="button"
                            className="button button-primary"
                            disabled={isLoading}
                            onClick={() =>
                                searchHotels(latitude, longitude, radiusKm)
                            }
                        >
                            🔍 Rechercher
                        </button>

                        <button
                            type="button"
                            className="button button-secondary"
                            disabled={isLoading}
                            onClick={useCurrentPosition}
                        >
                            📍 Utiliser ma position GPS
                        </button>

                        <div className={`status ${status.type}`}>
                            {status.message}
                        </div>
                    </section>

                    {selectedHotel && (
                        <section className="panel card">
                            <h3>🧭 Itinéraire</h3>

                            <p
                                style={{
                                    margin: "0 0 12px",
                                    fontSize: "12px",
                                    color: "var(--color-muted)",
                                }}
                            >
                                Vers <strong>{selectedHotel.name}</strong>
                            </p>

                            <div className="travel-modes">
                                {TRAVEL_MODES.map((mode) => (
                                    <div
                                        key={mode.profile}
                                        className={
                                            "travel-mode" +
                                            (selectedProfile === mode.profile
                                                ? " active"
                                                : "")
                                        }
                                        onClick={() =>
                                            setSelectedProfile(mode.profile)
                                        }
                                    >
                                        <span className="travel-mode-icon">
                                            {mode.icon}
                                        </span>
                                        {mode.label}
                                    </div>
                                ))}
                            </div>

                            {route && (
                                <div className="route-summary visible">
                                    <div className="route-stat distance">
                                        <div className="value">
                                            {formatDistance(
                                                route.distance_metres,
                                            )}
                                        </div>
                                        <div className="label">
                                            Distance route
                                        </div>
                                    </div>

                                    <div className="route-stat duration">
                                        <div className="value">
                                            {formatDuration(
                                                route.duration_seconds,
                                            )}
                                        </div>
                                        <div className="label">
                                            Durée estimée
                                        </div>
                                    </div>
                                </div>
                            )}
                        </section>
                    )}

                    <section className="panel card results-panel">
                        <div className="results-header">
                            <h3
                                style={{
                                    textTransform: "none",
                                    letterSpacing: "normal",
                                    margin: 0,
                                }}
                            >
                                Résultats
                            </h3>

                            <span className="result-count">
                                {hotels.length} hôtel
                                {hotels.length > 1 ? "s" : ""}
                            </span>
                        </div>

                        <div className="results-list">
                            {hotels.length === 0 && (
                                <p className="empty-message">
                                    Aucun résultat à afficher.
                                </p>
                            )}

                            {hotels.map((hotel, index) => (
                                <article
                                    key={hotel.id}
                                    className={
                                        "hotel-card" +
                                        (selectedHotel?.id === hotel.id
                                            ? " selected"
                                            : "")
                                    }
                                    onClick={() => setSelectedHotel(hotel)}
                                >
                                    <div className="hotel-rank">
                                        {index + 1}
                                    </div>

                                    <div className="hotel-info">
                                        <h4>{hotel.name}</h4>
                                        <p>{starsLabel(hotel.stars)}</p>
                                    </div>

                                    <div className="hotel-distance">
                                        {formatDistance(
                                            hotel.distance_metres,
                                        )}
                                    </div>
                                </article>
                            ))}
                        </div>
                    </section>
                </aside>

                <section className="card map-card">
                    <MapContainer
                        center={[latitude, longitude]}
                        zoom={13}
                        className="leaflet-map"
                    >
                        <TileLayer
                            attribution="&copy; OpenStreetMap contributors"
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />

                        <MapClickHandler onMapClick={handleMapClick} />
                        <FitBounds points={fitPoints} />

                        {reference && (
                            <>
                                <Marker
                                    position={[
                                        reference.latitude,
                                        reference.longitude,
                                    ]}
                                    icon={referenceIcon}
                                >
                                    <Popup>
                                        <strong>
                                            Point de référence
                                        </strong>
                                        <br />
                                        Latitude :{" "}
                                        {reference.latitude.toFixed(5)}
                                        <br />
                                        Longitude :{" "}
                                        {reference.longitude.toFixed(5)}
                                    </Popup>
                                </Marker>

                                <Circle
                                    center={[
                                        reference.latitude,
                                        reference.longitude,
                                    ]}
                                    radius={radiusKm * 1000}
                                    pathOptions={{
                                        color: "#e8590c",
                                        fillColor: "#e8590c",
                                        fillOpacity: 0.07,
                                        weight: 1.5,
                                        dashArray: "6 6",
                                    }}
                                />
                            </>
                        )}

                        {hotels.map((hotel) => (
                            <Marker
                                key={hotel.id}
                                position={[hotel.latitude, hotel.longitude]}
                                eventHandlers={{
                                    click: () => setSelectedHotel(hotel),
                                }}
                            >
                                <Popup>
                                    <strong>{hotel.name}</strong>
                                    <br />
                                    {hotel.address ||
                                        "Adresse non disponible"}
                                    <br />
                                    {starsLabel(hotel.stars)}
                                    <br />
                                    Distance :{" "}
                                    {formatDistance(hotel.distance_metres)}
                                </Popup>
                            </Marker>
                        ))}

                        {routeLatLngs && (
                            <Polyline
                                positions={routeLatLngs}
                                pathOptions={{
                                    color: "#1b2a4a",
                                    weight: 4,
                                    opacity: 0.85,
                                }}
                            />
                        )}
                    </MapContainer>
                </section>
            </div>
        </main>
    );
}
