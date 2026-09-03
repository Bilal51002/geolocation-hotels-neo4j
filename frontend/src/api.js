import axios from "axios";

/*
 * En développement (npm run dev), Vite proxifie /api vers le
 * backend Flask (voir vite.config.js). En production, c'est
 * Nginx qui joue ce rôle (voir nginx.conf). Dans les deux cas,
 * on peut donc appeler des chemins relatifs commençant par
 * /api, sans jamais coder l'adresse du backend en dur.
 */

const client = axios.create({
    baseURL: "/api",
});

export async function fetchNearbyHotels(latitude, longitude, radiusMetres) {
    const response = await client.get("/hotels/nearby", {
        params: {
            lat: latitude,
            lon: longitude,
            radius: radiusMetres,
        },
    });

    return response.data;
}

export async function importNearbyHotels(latitude, longitude, radiusMetres) {
    const response = await client.post("/hotels/import-nearby", {
        lat: latitude,
        lon: longitude,
        radius: radiusMetres,
    });

    return response.data;
}

export async function fetchRoute(
    startLatitude,
    startLongitude,
    endLatitude,
    endLongitude,
    profile,
) {
    const response = await client.get("/route", {
        params: {
            start_lat: startLatitude,
            start_lon: startLongitude,
            end_lat: endLatitude,
            end_lon: endLongitude,
            profile,
        },
    });

    return response.data;
}

export async function fetchDashboardStats() {
    const response = await client.get("/dashboard/stats");
    return response.data;
}
