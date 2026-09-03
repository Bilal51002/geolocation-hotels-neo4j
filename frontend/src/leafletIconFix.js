import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

/*
 * Par défaut, Leaflet essaie de charger ses icônes de marqueur
 * via des chemins relatifs qui ne fonctionnent pas une fois le
 * projet packagé par Vite. On les redéclare explicitement en
 * s'appuyant sur les fichiers fournis par le package "leaflet".
 */

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
});
