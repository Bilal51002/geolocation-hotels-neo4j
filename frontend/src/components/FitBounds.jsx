import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

export default function FitBounds({ points }) {
    const map = useMap();

    useEffect(() => {
        if (!points || points.length === 0) {
            return;
        }

        const bounds = L.latLngBounds(points);

        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [40, 40] });
        }
    }, [points, map]);

    return null;
}
