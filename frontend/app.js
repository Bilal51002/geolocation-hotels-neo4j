const CASABLANCA_POSITION = {
    latitude: 33.5731,
    longitude: -7.5898
};

const map = L.map("map").setView(
    [
        CASABLANCA_POSITION.latitude,
        CASABLANCA_POSITION.longitude
    ],
    13
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
    }
).addTo(map);


const markersLayer = L.layerGroup().addTo(map);

const radiusSelect = document.getElementById("radius");
const locationButton = document.getElementById("locationButton");
const statusElement = document.getElementById("status");
const resultsElement = document.getElementById("results");
const resultCountElement = document.getElementById(
    "resultCount"
);


function updateStatus(message, type = "") {
    statusElement.textContent = message;
    statusElement.className = "status";

    if (type) {
        statusElement.classList.add(type);
    }
}


function setButtonsDisabled(disabled) {
    locationButton.disabled = disabled;
}


function formatDistance(distanceMetres) {
    if (distanceMetres < 1000) {
        return `${Math.round(distanceMetres)} m`;
    }

    const distanceKilometres = distanceMetres / 1000;

    return `${distanceKilometres.toFixed(2)} km`;
}


function createStars(stars) {
    if (!stars) {
        return "Nombre d'étoiles non disponible";
    }

    return `${"★".repeat(stars)} ${stars} étoile(s)`;
}


function clearMap() {
    markersLayer.clearLayers();
}


function displayHotels(
    hotels,
    userLatitude,
    userLongitude,
    radius
) {
    clearMap();

    const mapElements = [];

    const userMarker = L.marker(
        [
            userLatitude,
            userLongitude
        ]
    )
        .addTo(markersLayer)
        .bindPopup(
            `
                <strong>Votre point de référence</strong>
                <br>
                Latitude : ${userLatitude.toFixed(5)}
                <br>
                Longitude : ${userLongitude.toFixed(5)}
            `
        );

    mapElements.push(userMarker);

    const radiusCircle = L.circle(
        [
            userLatitude,
            userLongitude
        ],
        {
            radius: radius
        }
    ).addTo(markersLayer);

    mapElements.push(radiusCircle);

    hotels.forEach((hotel, index) => {
        const hotelMarker = L.marker(
            [
                hotel.latitude,
                hotel.longitude
            ]
        )
            .addTo(markersLayer)
            .bindPopup(
                `
                    <strong>${hotel.name}</strong>
                    <br>
                    ${hotel.address || "Adresse non disponible"}
                    <br>
                    ${createStars(hotel.stars)}
                    <br>
                    Distance :
                    ${formatDistance(hotel.distance_metres)}
                `
            );

        hotelMarker.on("click", () => {
            map.setView(
                [
                    hotel.latitude,
                    hotel.longitude
                ],
                16
            );
        });

        mapElements.push(hotelMarker);
    });

    const featureGroup = L.featureGroup(mapElements);

    if (featureGroup.getBounds().isValid()) {
        map.fitBounds(
            featureGroup.getBounds(),
            {
                padding: [35, 35]
            }
        );
    }
}


function displayResults(hotels) {
    resultsElement.innerHTML = "";

    const count = hotels.length;

    resultCountElement.textContent =
        `${count} résultat${count > 1 ? "s" : ""}`;

    if (count === 0) {
        resultsElement.innerHTML = `
            <p class="empty-message">
                Aucun hôtel n'a été trouvé dans ce rayon.
            </p>
        `;

        return;
    }

    hotels.forEach((hotel, index) => {
        const hotelCard = document.createElement("article");

        hotelCard.className = "hotel-card";

        hotelCard.innerHTML = `
            <div class="hotel-rank">
                ${index + 1}
            </div>

            <div class="hotel-information">
                <h3>${hotel.name}</h3>

                <p>
                    ${hotel.address || "Adresse non disponible"}
                </p>

                <p>
                    ${createStars(hotel.stars)}
                </p>
            </div>

            <div class="hotel-distance">
                ${formatDistance(hotel.distance_metres)}
            </div>
        `;

        hotelCard.addEventListener("click", () => {
            map.setView(
                [
                    hotel.latitude,
                    hotel.longitude
                ],
                16
            );
        });

        resultsElement.appendChild(hotelCard);
    });
}


async function fetchNearbyHotels(
    latitude,
    longitude,
    radius
) {
    const parameters = new URLSearchParams({
        lat: latitude.toString(),
        lon: longitude.toString(),
        radius: radius.toString()
    });

    const response = await fetch(
        `/api/hotels/nearby?${parameters.toString()}`
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error ||
            "Erreur pendant la recherche des hôtels."
        );
    }

    return data;
}


async function importNearbyHotels(
    latitude,
    longitude,
    radius
) {
    const response = await fetch(
        "/api/hotels/import-nearby",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                lat: latitude,
                lon: longitude,
                radius: radius
            })
        }
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error ||
            "Erreur pendant l'importation OpenStreetMap."
        );
    }

    return data;
}

async function searchHotels(latitude, longitude) {
    const radius = Number(radiusSelect.value);

    setButtonsDisabled(true);

    updateStatus(
        "Recherche des hôtels dans la base Neo4j...",
        "loading"
    );

    try {
        let searchData = await fetchNearbyHotels(
            latitude,
            longitude,
            radius
        );

        /*
         * Si aucun hôtel n'est présent dans Neo4j,
         * télécharger automatiquement les données OSM.
         */
        if (searchData.count === 0) {
            updateStatus(
                "Aucun hôtel dans la base pour cette zone. " +
                "Importation depuis OpenStreetMap en cours...",
                "loading"
            );

            const importData = await importNearbyHotels(
                latitude,
                longitude,
                radius
            );

            updateStatus(
                `${importData.imported_count} hôtel(s) ` +
                "importé(s). Nouvelle recherche...",
                "loading"
            );

            searchData = await fetchNearbyHotels(
                latitude,
                longitude,
                radius
            );
        }

        displayHotels(
            searchData.hotels,
            latitude,
            longitude,
            radius
        );

        displayResults(
            searchData.hotels
        );

        if (searchData.count === 0) {
            updateStatus(
                "Aucun hôtel OpenStreetMap n'a été trouvé " +
                `dans un rayon de ${formatDistance(radius)}.`,
                "success"
            );

            return;
        }

        updateStatus(
            `${searchData.count} hôtel(s) trouvé(s) ` +
            `dans un rayon de ${formatDistance(radius)}.`,
            "success"
        );

    } catch (error) {
        console.error(error);

        clearMap();

        resultsElement.innerHTML = `
            <p class="empty-message">
                Impossible de récupérer les résultats.
            </p>
        `;

        resultCountElement.textContent =
            "0 résultat";

        updateStatus(
            error.message,
            "error"
        );

    } finally {
        setButtonsDisabled(false);
    }
}


function useCurrentPosition() {
    if (!navigator.geolocation) {
        updateStatus(
            "La géolocalisation n'est pas prise en charge " +
            "par votre navigateur.",
            "error"
        );

        return;
    }

    setButtonsDisabled(true);

    updateStatus(
        "Récupération de votre position...",
        "loading"
    );

    navigator.geolocation.getCurrentPosition(
        position => {
            searchHotels(
                position.coords.latitude,
                position.coords.longitude
            );
        },

        error => {
            setButtonsDisabled(false);

            let message =
                "Impossible de récupérer votre position.";

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

            updateStatus(
                message,
                "error"
            );
        },

        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 30000
        }
    );
}


locationButton.addEventListener(
    "click",
    useCurrentPosition
);