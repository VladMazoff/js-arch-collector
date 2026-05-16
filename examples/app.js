// =============================================
// app.js — Architecture Test File
// =============================================

let selectedRoofs = [];
let currentFilters = { price: [0, 1000000], area: [50, 300] };
let mapInstance = null;
let isExporting = false;
let userFavorites = [];
let renderedCount = 0;

const config = {
    apiBase: "https://api.example.com",
    defaultCenter: [55.75, 37.61]
};

// IIFE для инициализации
(function initModule() {
    console.log("Module initialized");
})();

// ====================== UI / Events ======================
function bindEvents() {
    document.getElementById("filterBtn").addEventListener("click", applyFilters);
    document.getElementById("exportBtn").addEventListener("click", handleExport);
}

function toggleFavorite(roofId) {
    if (userFavorites.includes(roofId)) {
        userFavorites = userFavorites.filter(id => id !== roofId);
    } else {
        userFavorites.push(roofId);
    }
    renderFavorites();
}

function resetFilters() {
    currentFilters = { price: [0, 1000000], area: [50, 300] };
    applyFilters();
}

// ====================== Map Orchestrator ======================
function initMap() {
    mapInstance = { /* mock leaflet/mapbox instance */ };
    console.log("Map initialized");
}

function applyLoc(location) {
    if (mapInstance) {
        // mapInstance.flyTo...
        console.log("Applied location:", location);
    }
}

function onChunk(data) {
    renderedCount += data.length;
    selectedRoofs = [...selectedRoofs, ...data];
    renderRoofsOnMap();
}

function clientFilter(roofs) {
    return roofs.filter(r => 
        r.price >= currentFilters.price[0] && 
        r.price <= currentFilters.price[1]
    );
}

// ====================== Data / API ======================
async function scheduleLoad() {
    try {
        const res = await fetch(`${config.apiBase}/roofs`);
        const data = await res.json();
        onChunk(data);
    } catch (e) {
        console.error(e);
    }
}

function recalcRenderedCount() {
    renderedCount = selectedRoofs.length;
    updateUI();
}

// ====================== Init & Boot ======================
function init() {
    console.log("=== App Starting ===");

    initMap();
    bindEvents();
    scheduleLoad();

    // Global entry point
    window.App = {
        init: init,
        toggleFavorite: toggleFavorite,
        resetFilters: resetFilters,
        getState: () => ({ selectedRoofs, currentFilters, renderedCount })
    };
}

// Arrow functions + closures
const debouncedSearch = (query) => {
    // debounce logic
    console.log("Searching:", query);
};

// Экспорт для модульной системы (если будет)
if (typeof module !== 'undefined') {
    module.exports = { init, toggleFavorite };
}

// Запуск
window.addEventListener("DOMContentLoaded", init);
