export function formatDistance(distanceMetres) {
    if (distanceMetres < 1000) {
        return `${Math.round(distanceMetres)} m`;
    }

    return `${(distanceMetres / 1000).toFixed(2)} km`;
}

export function formatDuration(durationSeconds) {
    const minutes = Math.round(durationSeconds / 60);

    if (minutes < 60) {
        return `${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
}

export function starsLabel(stars) {
    if (!stars) {
        return "Non classé";
    }

    return "★".repeat(stars) + " " + stars + "/5";
}

export function starsGlyphs(stars) {
    const filled = stars || 0;
    return "★".repeat(filled) + "☆".repeat(5 - filled);
}
