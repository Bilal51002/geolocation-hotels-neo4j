const CHART_COLORS = [
    "#e8590c",
    "#f2a154",
    "#1b2a4a",
    "#2563eb",
    "#1e7b34",
    "#a8790a",
    "#a62525",
    "#6b7280",
];

const subtitleElement = document.getElementById("pageSubtitle");
const contentElement = document.getElementById("dashboardContent");
const emptyElement = document.getElementById("dashboardEmpty");

function createStarsText(stars) {
    return "★".repeat(stars) + "☆".repeat(5 - stars);
}

function renderStatCards(stats) {
    document.getElementById("statTotal").textContent = stats.total;
    document.getElementById("statStars").textContent =
        stats.with_stars;
    document.getElementById("statPhone").textContent =
        stats.with_phone;
    document.getElementById("statAddress").textContent =
        stats.with_address;
}

function renderZoneChart(zones) {
    const canvas = document.getElementById("zoneChart");

    new Chart(canvas, {
        type: "pie",
        data: {
            labels: zones.map((zone) => zone.zone),
            datasets: [
                {
                    data: zones.map((zone) => zone.count),
                    backgroundColor: CHART_COLORS,
                    borderColor: "#ffffff",
                    borderWidth: 2,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { boxWidth: 12, font: { size: 11 } },
                },
            },
        },
    });
}

function renderDistanceChart(distribution) {
    const canvas = document.getElementById("distanceChart");

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: distribution.map((item) => item.band),
            datasets: [
                {
                    label: "Hôtels",
                    data: distribution.map((item) => item.count),
                    backgroundColor: "#e8590c",
                    borderRadius: 6,
                    maxBarThickness: 46,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                },
            },
        },
    });
}

function renderTopHotels(topHotels) {
    const grid = document.getElementById("topHotelsGrid");
    grid.innerHTML = "";

    if (topHotels.length === 0) {
        grid.innerHTML = `
            <p class="empty-message">
                Aucun hôtel classé par étoiles pour le moment.
            </p>
        `;

        return;
    }

    topHotels.forEach((hotel) => {
        const card = document.createElement("div");
        card.className = "card top-hotel-card";

        card.innerHTML = `
            <h4>🏨 ${hotel.name}</h4>
            <div class="top-hotel-stars">
                ${createStarsText(hotel.stars)}
            </div>
            <p>📍 ${hotel.address || "Adresse non disponible"}</p>
        `;

        grid.appendChild(card);
    });
}

async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard/stats");
        const stats = await response.json();

        if (!response.ok) {
            throw new Error(
                stats.error ||
                "Impossible de charger les statistiques.",
            );
        }

        if (stats.total === 0) {
            emptyElement.style.display = "block";
            subtitleElement.textContent =
                "Aucune donnée pour le moment.";

            return;
        }

        subtitleElement.textContent =
            `Analyse des ${stats.total} hôtels extraits d'OpenStreetMap`;

        contentElement.style.display = "block";

        renderStatCards(stats);
        renderZoneChart(
            stats.zones.length
                ? stats.zones
                : [{ zone: "Non renseigné", count: stats.total }],
        );
        renderDistanceChart(stats.distance_distribution);
        renderTopHotels(stats.top_hotels);

    } catch (error) {
        console.error(error);

        subtitleElement.textContent = error.message;
        emptyElement.style.display = "block";
        emptyElement.querySelector("p").innerHTML =
            "Impossible de charger les statistiques.<br>" +
            error.message;
    }
}

loadDashboard();
