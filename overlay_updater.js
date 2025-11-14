/**
 * Overlay Stats Updater
 * Script para actualizar dinámicamente las estadísticas del overlay
 *
 * USO:
 * 1. Crea un archivo stats.json con tus datos
 * 2. Incluye este script en el HTML o úsalo con un servidor local
 * 3. Las stats se actualizarán automáticamente cada X segundos
 */

// Configuración
const CONFIG = {
    updateInterval: 5000, // Actualizar cada 5 segundos
    statsFile: 'stats.json', // Ruta al archivo JSON con los datos
    useLocalFile: false, // Cambiar a true si usas archivo local
    useMockData: true, // Cambiar a true para datos de prueba
};

// Mock data para testing (puedes eliminar esto en producción)
function getMockStats() {
    const baseRealized = 1247.50;
    const baseUnrealized = -328.75;

    return {
        winStreak: Math.floor(Math.random() * 20) + 5,
        realizedPL: baseRealized + (Math.random() * 200 - 100),
        unrealizedPL: baseUnrealized + (Math.random() * 100 - 50),
        totalPL: 0 // Se calculará automáticamente
    };
}

// Función para actualizar el DOM
function updateStatsUI(stats) {
    const statBoxes = document.querySelectorAll('.stat-value');

    if (statBoxes.length >= 4) {
        // Win Streak
        statBoxes[0].textContent = stats.winStreak;

        // Realized P/L
        const realizedValue = stats.realizedPL;
        statBoxes[1].textContent = formatCurrency(realizedValue);
        statBoxes[1].className = 'stat-value ' + (realizedValue >= 0 ? 'positive' : 'negative');

        // Unrealized P/L
        const unrealizedValue = stats.unrealizedPL;
        statBoxes[2].textContent = formatCurrency(unrealizedValue);
        statBoxes[2].className = 'stat-value ' + (unrealizedValue >= 0 ? 'positive' : 'negative');

        // Total P/L
        const totalValue = realizedValue + unrealizedValue;
        statBoxes[3].textContent = formatCurrency(totalValue);
        statBoxes[3].className = 'stat-value ' + (totalValue >= 0 ? 'positive' : 'negative');
    }
}

// Formatear valores de moneda
function formatCurrency(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}$${Math.abs(value).toFixed(2)}`;
}

// Cargar stats desde archivo JSON
async function loadStatsFromFile() {
    try {
        const response = await fetch(CONFIG.statsFile);
        if (!response.ok) throw new Error('No se pudo cargar el archivo');

        const stats = await response.json();
        return stats;
    } catch (error) {
        console.error('Error cargando stats:', error);
        return null;
    }
}

// Cargar stats desde API (ejemplo)
async function loadStatsFromAPI() {
    try {
        // Reemplaza con tu endpoint real
        const response = await fetch('http://localhost:3000/api/stats');
        if (!response.ok) throw new Error('Error en la API');

        const stats = await response.json();
        return stats;
    } catch (error) {
        console.error('Error cargando stats desde API:', error);
        return null;
    }
}

// Función principal de actualización
async function updateStats() {
    let stats;

    if (CONFIG.useMockData) {
        stats = getMockStats();
    } else if (CONFIG.useLocalFile) {
        stats = await loadStatsFromFile();
    } else {
        stats = await loadStatsFromAPI();
    }

    if (stats) {
        updateStatsUI(stats);
        console.log('Stats actualizadas:', stats);
    }
}

// Iniciar actualizaciones automáticas
function startAutoUpdate() {
    console.log('Iniciando actualización automática de stats...');
    updateStats(); // Actualizar inmediatamente
    setInterval(updateStats, CONFIG.updateInterval);
}

// Conectar con WebSocket (para actualizaciones en tiempo real)
function connectWebSocket(url = 'ws://localhost:8080') {
    const ws = new WebSocket(url);

    ws.onopen = () => {
        console.log('WebSocket conectado');
    };

    ws.onmessage = (event) => {
        try {
            const stats = JSON.parse(event.data);
            updateStatsUI(stats);
            console.log('Stats actualizadas via WebSocket:', stats);
        } catch (error) {
            console.error('Error parseando mensaje WebSocket:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('Error en WebSocket:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket desconectado. Reconectando en 5s...');
        setTimeout(() => connectWebSocket(url), 5000);
    };

    return ws;
}

// Exportar funciones para uso manual
window.overlayUpdater = {
    updateStats,
    startAutoUpdate,
    connectWebSocket,
    updateStatsUI,
    CONFIG
};

// Auto-iniciar si se detecta que el DOM está listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startAutoUpdate);
} else {
    startAutoUpdate();
}

// ============================================
// EJEMPLOS DE USO
// ============================================

/*

EJEMPLO 1: Usar archivo JSON local
-----------------------------------
1. Crea un archivo "stats.json" en la misma carpeta:
{
    "winStreak": 15,
    "realizedPL": 1247.50,
    "unrealizedPL": -328.75
}

2. En overlay_updater.js, cambia:
CONFIG.useLocalFile = true;
CONFIG.useMockData = false;


EJEMPLO 2: Conectar a una API
------------------------------
1. En overlay_updater.js, cambia:
CONFIG.useMockData = false;
CONFIG.useLocalFile = false;

2. Modifica la función loadStatsFromAPI() con tu endpoint


EJEMPLO 3: WebSocket en tiempo real
------------------------------------
1. En el HTML, después de cargar este script, añade:
<script>
    overlayUpdater.connectWebSocket('ws://localhost:8080');
</script>

2. Tu servidor WebSocket debe enviar mensajes en formato JSON:
{
    "winStreak": 15,
    "realizedPL": 1247.50,
    "unrealizedPL": -328.75
}


EJEMPLO 4: Actualización manual desde consola
----------------------------------------------
Abre la consola del navegador (F12) y ejecuta:

overlayUpdater.updateStatsUI({
    winStreak: 20,
    realizedPL: 2500.00,
    unrealizedPL: -150.00
});


EJEMPLO 5: Integración con tu bot de trading
---------------------------------------------
Desde tu bot de Python/Node.js, puedes:

// Node.js
const fs = require('fs');
const stats = {
    winStreak: calculateWinStreak(),
    realizedPL: getTotalRealizedPL(),
    unrealizedPL: getTotalUnrealizedPL()
};
fs.writeFileSync('stats.json', JSON.stringify(stats));

# Python
import json
stats = {
    "winStreak": calculate_win_streak(),
    "realizedPL": get_total_realized_pl(),
    "unrealizedPL": get_total_unrealized_pl()
}
with open('stats.json', 'w') as f:
    json.dump(stats, f)


EJEMPLO 6: Stream Deck + HTTP Server
-------------------------------------
Crea un servidor HTTP simple que reciba actualizaciones:

const express = require('express');
const app = express();
const PORT = 3000;

let currentStats = {
    winStreak: 0,
    realizedPL: 0,
    unrealizedPL: 0
};

app.use(express.json());

app.post('/update', (req, res) => {
    currentStats = { ...currentStats, ...req.body };
    res.json({ success: true });
});

app.get('/stats', (req, res) => {
    res.json(currentStats);
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

*/
