/* ============================================================
   ÉTAT GLOBAL
   ============================================================ */

let currentHotels = [];
let currentReference = null;
let selectedHotel = null;
let selectedProfile = "foot";

/* ============================================================
   INITIALISATION DE LA CARTE
   ============================================================ */

const DEFAULT_POSITION = {
    latitude: 34.0331,
    longitude: -5.0003,
};

const map = L.map("map").setView(
    [DEFAULT_POSITION.latitude, DEFAULT_POSITION.longitude],
    13
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }
).addTo(map);

const markersLayer = L.layerGroup().addTo(map);
const routeLayer = L.layerGroup().addTo(map);

/* ============================================================
   ÉLÉMENTS DU DOM
   ============================================================ */

const latitudeInput = document.getElementById("latitude");
const longitudeInput = document.getElementById("longitude");
const radiusInput = document.getElementById("radius");
const radiusValueLabel = document.getElementById("radiusValue");
const searchButton = document.getElementById("searchButton");
const locationButton = document.getElementById("locationButton");
const statusElement = document.getElementById("status");
const resultsElement = document.getElementById("results");
const resultCountElement = document.getElementById("resultCount");
const itineraryPanel = document.getElementById("itineraryPanel");
const routeSummary = document.getElementById("routeSummary");
const routeDistanceLabel = document.getElementById("routeDistance");
const routeDurationLabel = document.getElementById("routeDuration");
const travelModeButtons = document.querySelectorAll(".travel-mode");

/* ============================================================
   UTILITAIRES D'AFFICHAGE
   ============================================================ */

function updateStatus(message, type = "") {
    statusElement.textContent = message;
    statusElement.className = "status";

    if (type) {
        statusElement.classList.add(type);
    }
}

function setControlsDisabled(disabled) {
    searchButton.disabled = disabled;
    locationButton.disabled = disabled;
}

function formatDistance(distanceMetres) {
    if (distanceMetres < 1000) {
        return `${Math.round(distanceMetres)} m`;
    }

    return `${(distanceMetres / 1000).toFixed(2)} km`;
}

function formatDuration(durationSeconds) {
    const minutes = Math.round(durationSeconds / 60);

    if (minutes < 60) {
        return `${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
}

function createStars(stars) {
    if (!stars) {
        return "Non classé";
    }

    return "★".repeat(stars) + " " + stars + "/5";
}

/* ============================================================
   SLIDER DE RAYON
   ============================================================ */

radiusInput.addEventListener("input", () => {
    radiusValueLabel.textContent = `${radiusInput.value} km`;
});

/* ============================================================
   CLIC SUR LA CARTE POUR CHOISIR LA POSITION
   ============================================================ */

let referenceMarker = null;

map.on("click", (event) => {
    latitudeInput.value = event.latlng.lat.toFixed(5);
    longitudeInput.value = event.latlng.lng.toFixed(5);

    updateStatus(
        "Position sélectionnée sur la carte. " +
        "Cliquez sur Rechercher.",
    );
});

/* ============================================================
   AFFICHAGE DES RÉSULTATS SUR LA CARTE
   ============================================================ */

function clearMarkers() {
    markersLayer.clearLayers();
}

function clearRoute() {
    routeLayer.clearLayers();
    routeSummary.classList.remove("visible");
}

function displayHotelsOnMap(hotels, refLat, refLon, radiusKm) {
    clearMarkers();

    const mapElements = [];

    if (referenceMarker) {
        referenceMarker = null;
    }

    referenceMarker = L.marker([refLat, refLon], {
        title: "Votre position",
    })
        .addTo(markersLayer)
        .bindPopup(
            "<strong>Point de référence</strong><br>" +
            `Latitude : ${refLat.toFixed(5)}<br>` +
            `Longitude : ${refLon.toFixed(5)}`,
        );

    mapElements.push(referenceMarker);

    const radiusCircle = L.circle([refLat, refLon], {
        radius: radiusKm * 1000,
        color: "#e8590c",
        fillColor: "#e8590c",
        fillOpacity: 0.07,
        weight: 1.5,
        dashArray: "6 6",
    }).addTo(markersLayer);

    mapElements.push(radiusCircle);

    hotels.forEach((hotel) => {
        const marker = L.marker([hotel.latitude, hotel.longitude])
            .addTo(markersLayer)
            .bindPopup(
                `<strong>${hotel.name}</strong><br>` +
                `${hotel.address || "Adresse non disponible"}<br>` +
                `${createStars(hotel.stars)}<br>` +
                `Distance : ${formatDistance(hotel.distance_metres)}`,
            );

        marker.on("click", () => selectHotel(hotel));

        hotel._marker = marker;
        mapElements.push(marker);
    });

    const featureGroup = L.featureGroup(mapElements);

    if (featureGroup.getBounds().isValid()) {
        map.fitBounds(featureGroup.getBounds(), {
            padding: [35, 35],
        });
    }
}

/* ============================================================
   LISTE DES RÉSULTATS
   ============================================================ */

function displayResultsList(hotels) {
    resultsElement.innerHTML = "";

    const count = hotels.length;

    resultCountElement.textContent =
        `${count} hôtel${count > 1 ? "s" : ""}`;

    if (count === 0) {
        resultsElement.innerHTML = `
            <p class="empty-message">
                Aucun hôtel trouvé dans ce rayon.
            </p>
        `;

        return;
    }

    hotels.forEach((hotel, index) => {
        const card = document.createElement("article");
        card.className = "hotel-card";
        card.dataset.hotelId = hotel.id;

        card.innerHTML = `
            <div class="hotel-rank">${index + 1}</div>

            <div class="hotel-info">
                <h4>${hotel.name}</h4>
                <p>${createStars(hotel.stars)}</p>
            </div>

            <div class="hotel-distance">
                ${formatDistance(hotel.distance_metres)}
            </div>
        `;

        card.addEventListener("click", () => selectHotel(hotel));

        resultsElement.appendChild(card);
    });
}

/* ============================================================
   SÉLECTION D'UN HÔTEL ET CALCUL D'ITINÉRAIRE
   ============================================================ */

function highlightSelectedCard(hotelId) {
    document.querySelectorAll(".hotel-card").forEach((card) => {
        card.classList.toggle(
            "selected",
            card.dataset.hotelId === String(hotelId),
        );
    });
}

async function selectHotel(hotel) {
    selectedHotel = hotel;

    highlightSelectedCard(hotel.id);

    if (hotel._marker) {
        map.setView([hotel.latitude, hotel.longitude], 15);
        hotel._marker.openPopup();
    }

    itineraryPanel.style.display = "block";

    await computeAndDrawRoute();
}

async function fetchRoute(startLat, startLon, endLat, endLon, profile) {
    const parameters = new URLSearchParams({
        start_lat: startLat,
        start_lon: startLon,
        end_lat: endLat,
        end_lon: endLon,
        profile: profile,
    });

    const response = await fetch(`/api/route?${parameters}`);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || "Impossible de calculer l'itinéraire.",
        );
    }

    return data;
}

async function computeAndDrawRoute() {
    if (!selectedHotel || !currentReference) {
        return;
    }

    clearRoute();

    try {
        const route = await fetchRoute(
            currentReference.latitude,
            currentReference.longitude,
            selectedHotel.latitude,
            selectedHotel.longitude,
            selectedProfile,
        );

        const latLngs = route.geometry.coordinates.map(
            ([lon, lat]) => [lat, lon],
        );

        const polyline = L.polyline(latLngs, {
            color: "#1b2a4a",
            weight: 4,
            opacity: 0.85,
        }).addTo(routeLayer);

        map.fitBounds(polyline.getBounds(), {
            padding: [40, 40],
        });

        routeDistanceLabel.textContent =
            formatDistance(route.distance_metres);

        routeDurationLabel.textContent =
            formatDuration(route.duration_seconds);

        routeSummary.classList.add("visible");

    } catch (error) {
        console.error(error);

        updateStatus(
            "Itinéraire indisponible : " + error.message,
            "error",
        );
    }
}

travelModeButtons.forEach((button) => {
    button.addEventListener("click", () => {
        travelModeButtons.forEach((element) =>
            element.classList.remove("active"),
        );

        button.classList.add("active");

        selectedProfile = button.dataset.profile;

        computeAndDrawRoute();
    });
});

/* ============================================================
   APPELS API — RECHERCHE / IMPORTATION
   ============================================================ */

async function fetchNearbyHotels(latitude, longitude, radiusMetres) {
    const parameters = new URLSearchParams({
        lat: latitude.toString(),
        lon: longitude.toString(),
        radius: radiusMetres.toString(),
    });

    const response = await fetch(
        `/api/hotels/nearby?${parameters}`,
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || "Erreur pendant la recherche des hôtels.",
        );
    }

    return data;
}

async function importNearbyHotels(latitude, longitude, radiusMetres) {
    const response = await fetch("/api/hotels/import-nearby", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            lat: latitude,
            lon: longitude,
            radius: radiusMetres,
        }),
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error ||
            "Erreur pendant l'importation OpenStreetMap.",
        );
    }

    return data;
}

/* ============================================================
   RECHERCHE PRINCIPALE
   ============================================================ */

async function searchHotels(latitude, longitude) {
    const radiusKm = Number(radiusInput.value);
    const radiusMetres = radiusKm * 1000;

    latitudeInput.value = latitude.toFixed(5);
    longitudeInput.value = longitude.toFixed(5);

    currentReference = { latitude, longitude };
    selectedHotel = null;
    itineraryPanel.style.display = "none";
    clearRoute();

    setControlsDisabled(true);

    updateStatus(
        "Recherche des hôtels dans la base Neo4j...",
        "loading",
    );

    try {
        let searchData = await fetchNearbyHotels(
            latitude,
            longitude,
            radiusMetres,
        );

        if (searchData.count === 0) {
            updateStatus(
                "Aucun hôtel en base pour cette zone. " +
                "Importation depuis OpenStreetMap...",
                "loading",
            );

            const importData = await importNearbyHotels(
                latitude,
                longitude,
                radiusMetres,
            );

            updateStatus(
                `${importData.imported_count} hôtel(s) importé(s). ` +
                "Nouvelle recherche...",
                "loading",
            );

            searchData = await fetchNearbyHotels(
                latitude,
                longitude,
                radiusMetres,
            );
        }

        currentHotels = searchData.hotels;

        displayHotelsOnMap(currentHotels, latitude, longitude, radiusKm);
        displayResultsList(currentHotels);

        if (searchData.count === 0) {
            updateStatus(
                `Aucun hôtel trouvé dans un rayon de ${radiusKm} km.`,
                "success",
            );

            return;
        }

        updateStatus(
            `${searchData.count} hôtel(s) trouvé(s) dans un rayon ` +
            `de ${radiusKm} km.`,
            "success",
        );

    } catch (error) {
        console.error(error);

        clearMarkers();

        resultsElement.innerHTML = `
            <p class="empty-message">
                Impossible de récupérer les résultats.
            </p>
        `;

        resultCountElement.textContent = "0 hôtel";

        updateStatus(error.message, "error");

    } finally {
        setControlsDisabled(false);
    }
}

/* ============================================================
   BOUTONS DE RECHERCHE ET DE GÉOLOCALISATION
   ============================================================ */

searchButton.addEventListener("click", () => {
    const latitude = Number(latitudeInput.value);
    const longitude = Number(longitudeInput.value);

    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        updateStatus(
            "Merci de saisir une latitude et une longitude valides.",
            "error",
        );

        return;
    }

    searchHotels(latitude, longitude);
});

function useCurrentPosition() {
    if (!navigator.geolocation) {
        updateStatus(
            "La géolocalisation n'est pas prise en charge " +
            "par votre navigateur.",
            "error",
        );

        return;
    }

    setControlsDisabled(true);

    updateStatus("Récupération de votre position...", "loading");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            searchHotels(
                position.coords.latitude,
                position.coords.longitude,
            );
        },

        (error) => {
            setControlsDisabled(false);

            let message = "Impossible de récupérer votre position.";

            if (error.code === error.PERMISSION_DENIED) {
                message = "Vous avez refusé l'accès à votre position.";
            }

            if (error.code === error.POSITION_UNAVAILABLE) {
                message = "Votre position est actuellement indisponible.";
            }

            if (error.code === error.TIMEOUT) {
                message =
                    "La récupération de la position a dépassé " +
                    "le délai autorisé.";
            }

            updateStatus(message, "error");
        },

        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000,
        },
    );
}

locationButton.addEventListener("click", useCurrentPosition);

/* ============================================================
   RECHERCHE INITIALE AUTOMATIQUE
   ============================================================ */

searchHotels(DEFAULT_POSITION.latitude, DEFAULT_POSITION.longitude);
