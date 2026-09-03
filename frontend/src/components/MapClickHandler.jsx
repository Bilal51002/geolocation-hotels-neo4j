import { useMapEvents } from "react-leaflet";

export default function MapClickHandler({ onMapClick }) {
    useMapEvents({
        click(event) {
            onMapClick(event.latlng.lat, event.latlng.lng);
        },
    });

    return null;
}
