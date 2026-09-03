import { NavLink } from "react-router-dom";

export default function Navbar() {
    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <div className="navbar-brand-icon">🏨</div>

                <div className="navbar-brand-text">
                    <h1>Hotel Finder</h1>
                    <span>Recherche géographique d'hôtels</span>
                </div>
            </div>

            <div className="navbar-tabs">
                <NavLink
                    to="/"
                    end
                    className={({ isActive }) =>
                        "navbar-tab" + (isActive ? " active" : "")
                    }
                >
                    🗺️ Carte
                </NavLink>

                <NavLink
                    to="/dashboard"
                    className={({ isActive }) =>
                        "navbar-tab" + (isActive ? " active" : "")
                    }
                >
                    📊 Dashboard
                </NavLink>
            </div>

            <div className="navbar-badges">
                <span className="navbar-badge">Neo4j</span>

                <span className="navbar-badge badge-orange">
                    OpenStreetMap
                </span>

                <span className="navbar-badge badge-green">
                    React
                </span>
            </div>
        </nav>
    );
}
