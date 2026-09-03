import { useEffect, useState } from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    Legend,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import { fetchDashboardStats } from "../api.js";
import { starsGlyphs } from "../format.js";

const CHART_COLORS = [
    "#e8590c",
    "#f2a154",
    "#1b2a4a",
    "#2563eb",
    "#1e7b34",
    "#a8790a",
];

export default function DashboardPage() {
    const [stats, setStats] = useState(null);
    const [errorMessage, setErrorMessage] = useState(null);

    useEffect(() => {
        let cancelled = false;

        async function loadStats() {
            try {
                const data = await fetchDashboardStats();

                if (!cancelled) {
                    setStats(data);
                }

            } catch (error) {
                console.error(error);

                if (!cancelled) {
                    setErrorMessage(
                        error?.response?.data?.error ||
                        error.message ||
                        "Impossible de charger les statistiques.",
                    );
                }
            }
        }

        loadStats();

        return () => {
            cancelled = true;
        };
    }, []);

    if (errorMessage) {
        return (
            <main className="page-container">
                <div className="page-header">
                    <h2>📊 Dashboard — Hotel Finder</h2>
                    <p>{errorMessage}</p>
                </div>

                <div className="card dashboard-empty">
                    <p>
                        Faites une recherche sur la{" "}
                        <a href="/">carte</a> pour importer des
                        hôtels depuis OpenStreetMap.
                    </p>
                </div>
            </main>
        );
    }

    if (!stats) {
        return (
            <main className="page-container">
                <div className="page-header">
                    <h2>📊 Dashboard — Hotel Finder</h2>
                    <p>Chargement des statistiques...</p>
                </div>
            </main>
        );
    }

    if (stats.total === 0) {
        return (
            <main className="page-container">
                <div className="page-header">
                    <h2>📊 Dashboard — Hotel Finder</h2>
                    <p>Aucune donnée pour le moment.</p>
                </div>

                <div className="card dashboard-empty">
                    <p>
                        Faites une recherche sur la{" "}
                        <a href="/">carte</a> pour importer des
                        hôtels depuis OpenStreetMap.
                    </p>
                </div>
            </main>
        );
    }

    const zones = stats.zones.length
        ? stats.zones
        : [{ zone: "Non renseigné", count: stats.total }];

    return (
        <main className="page-container">
            <div className="page-header">
                <h2>📊 Dashboard — Hotel Finder</h2>
                <p>
                    Analyse des {stats.total} hôtels extraits
                    d'OpenStreetMap
                </p>
            </div>

            <div className="stat-grid">
                <div className="card stat-card">
                    <div className="stat-icon orange">🏨</div>
                    <div className="stat-value">{stats.total}</div>
                    <div className="stat-label">Total hôtels</div>
                </div>

                <div className="card stat-card">
                    <div className="stat-icon yellow">⭐</div>
                    <div className="stat-value">
                        {stats.with_stars}
                    </div>
                    <div className="stat-label">Avec étoiles</div>
                </div>

                <div className="card stat-card">
                    <div className="stat-icon green">📞</div>
                    <div className="stat-value">
                        {stats.with_phone}
                    </div>
                    <div className="stat-label">Avec contact</div>
                </div>

                <div className="card stat-card">
                    <div className="stat-icon blue">📍</div>
                    <div className="stat-value">
                        {stats.with_address}
                    </div>
                    <div className="stat-label">Avec adresse</div>
                </div>
            </div>

            <div className="chart-grid">
                <div className="card chart-card">
                    <h3>🗺️ Répartition par zone</h3>

                    <div className="chart-canvas-wrap">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={zones}
                                    dataKey="count"
                                    nameKey="zone"
                                    cx="40%"
                                    cy="50%"
                                    outerRadius={90}
                                >
                                    {zones.map((entry, index) => (
                                        <Cell
                                            key={entry.zone}
                                            fill={
                                                CHART_COLORS[
                                                    index %
                                                    CHART_COLORS.length
                                                ]
                                            }
                                        />
                                    ))}
                                </Pie>

                                <Tooltip />

                                <Legend
                                    layout="vertical"
                                    align="right"
                                    verticalAlign="middle"
                                    wrapperStyle={{ fontSize: 12 }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="card chart-card">
                    <h3>📶 Distribution par distance</h3>

                    <div className="chart-canvas-wrap">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stats.distance_distribution}>
                                <CartesianGrid
                                    strokeDasharray="3 3"
                                    vertical={false}
                                />
                                <XAxis
                                    dataKey="band"
                                    tick={{ fontSize: 11 }}
                                />
                                <YAxis
                                    allowDecimals={false}
                                    tick={{ fontSize: 11 }}
                                />
                                <Tooltip />
                                <Bar
                                    dataKey="count"
                                    name="Hôtels"
                                    fill="#e8590c"
                                    radius={[6, 6, 0, 0]}
                                    maxBarSize={46}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <h3
                style={{
                    margin: "0 0 12px",
                    fontSize: "14px",
                    color: "var(--color-navy)",
                }}
            >
                ⭐ Hôtels classés par étoiles
            </h3>

            <div className="top-hotels-grid">
                {stats.top_hotels.length === 0 && (
                    <p className="empty-message">
                        Aucun hôtel classé par étoiles pour le
                        moment.
                    </p>
                )}

                {stats.top_hotels.map((hotel) => (
                    <div
                        key={hotel.name}
                        className="card top-hotel-card"
                    >
                        <h4>🏨 {hotel.name}</h4>

                        <div className="top-hotel-stars">
                            {starsGlyphs(hotel.stars)}
                        </div>

                        <p>
                            📍{" "}
                            {hotel.address || "Adresse non disponible"}
                        </p>
                    </div>
                ))}
            </div>

            <div className="card about-data">
                <h3>ⓘ À propos des données</h3>

                <div className="about-data-grid">
                    <div className="about-data-item">
                        <span style={{ fontSize: "16px" }}>🟢</span>
                        <div>
                            <span className="label">Source</span>
                            <span className="value">
                                OpenStreetMap via Overpass API
                            </span>
                        </div>
                    </div>

                    <div className="about-data-item">
                        <span style={{ fontSize: "16px" }}>🗄️</span>
                        <div>
                            <span className="label">Stockage</span>
                            <span className="value">
                                Neo4j Graph Database
                            </span>
                        </div>
                    </div>

                    <div className="about-data-item">
                        <span style={{ fontSize: "16px" }}>📏</span>
                        <div>
                            <span className="label">Distance</span>
                            <span className="value">
                                point.distance() natif Neo4j
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
