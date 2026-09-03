import { Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import MapPage from "./components/MapPage.jsx";
import DashboardPage from "./components/DashboardPage.jsx";

export default function App() {
    return (
        <>
            <Navbar />

            <Routes>
                <Route path="/" element={<MapPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
            </Routes>

            <footer className="footer">
                Données OpenStreetMap · Base géospatiale Neo4j ·
                Itinéraires calculés par OSRM
            </footer>
        </>
    );
}
