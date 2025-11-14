# 🎮💰 Crypto Gaming Stream Overlay

**Overlay profesional 1920x1080 para streaming simultáneo de Pokémon TCG Pocket y Trading de Bitcoin**

![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![OBS](https://img.shields.io/badge/OBS-Compatible-brightgreen.svg)

---

## 📸 Vista Previa

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CRYPTO × GAMING STREAM                                  │
├──────────────────┬──────────────────────────────────────────────────────────────┤
│                  │                                                              │
│   POKÉMON TCG    │                                                              │
│     POCKET       │              BTC TRADING PLATFORM                            │
│   [Vertical]     │                  [Horizontal]                                │
│    (iPhone)      │                                                              │
│                  │                                                              │
│                  │                                                   ┌─────────┐│
│                  │                                                   │ WEBCAM  ││
│                  │                                                   │  /LOGO  ││
├──────────────────┴───────────────────────────────────────────────────┴─────────┤
│  [Win Streak: 12]  [P/L Realizado: +$1,247.50]  [P/L No Realizado: -$328.75]  │
│                              [Total: +$918.75]                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ⚠️ NO ES CONSEJO DE INVERSIÓN · ENTRETENIMIENTO EDUCATIVO +18                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Características

✅ **Diseño profesional** con estética cripto-gaming
✅ **Paleta de colores**: Negro, gris oscuro, naranja Bitcoin (#F7931A)
✅ **Dos ventanas principales**: Vertical (9:16) + Horizontal (16:9)
✅ **HUD dinámico** con estadísticas en tiempo real
✅ **Animaciones suaves**: Logos cripto y decoraciones Pokémon flotando
✅ **Efectos de neón** y marco tech geométrico
✅ **Zona de webcam/logo** integrada
✅ **Aviso legal** incorporado
✅ **100% personalizable** vía HTML/CSS
✅ **Actualización automática** de stats desde Python/JavaScript

---

## 📦 Archivos Incluidos

```
stream_overlay.html          # Overlay principal (usar en OBS)
overlay_updater.js           # Script JavaScript para actualización dinámica
update_overlay_stats.py      # Script Python para integración con trading bot
stats.json                   # Archivo de datos para estadísticas
OVERLAY_GUIDE.md            # Guía completa de configuración y uso
OVERLAY_README.md           # Este archivo
```

---

## 🚀 Quick Start

### 1️⃣ **Configurar en OBS Studio**

1. Abre OBS Studio
2. Crea una nueva escena: `Crypto Gaming Stream`
3. Agrega una fuente **Browser Source**:
   - **Local file**: ✅ Marca esta opción
   - **Archivo**: Selecciona `stream_overlay.html`
   - **Ancho**: `1920`
   - **Alto**: `1080`
4. Agrega tus capturas de pantalla (iPhone + Trading platform)
5. Agrega tu webcam
6. **¡Listo para hacer stream!** 🎉

📖 **Guía detallada**: Ver `OVERLAY_GUIDE.md`

---

### 2️⃣ **Actualizar Estadísticas**

#### **Opción A: Manualmente (editar HTML)**

Abre `stream_overlay.html` y busca:

```html
<div class="stat-value">12</div>  <!-- Cambia el valor aquí -->
```

Guarda y refresca la fuente en OBS.

#### **Opción B: Desde línea de comandos**

```bash
python update_overlay_stats.py --win-streak 15 --realized 1247.50 --unrealized -328.75
```

#### **Opción C: Integración con tu bot de trading**

```python
from update_overlay_stats import OverlayStatsUpdater

overlay = OverlayStatsUpdater()

# Después de cada trade
overlay.update_stats(
    win_streak=15,
    realized_pl=1247.50,
    unrealized_pl=-328.75
)
```

#### **Opción D: WebSocket en tiempo real**

```javascript
// En tu servidor
ws.send(JSON.stringify({
    winStreak: 15,
    realizedPL: 1247.50,
    unrealizedPL: -328.75
}));
```

---

## 🎨 Personalización

### **Cambiar Colores**

Edita en `stream_overlay.html`:

```css
/* Naranja Bitcoin */
#F7931A

/* Verde (ganancias) */
#14F195

/* Rojo (pérdidas) */
#FF4444
```

### **Cambiar Tamaños de Ventanas**

```css
.overlay-container {
    grid-template-columns: 1fr 2fr;  /* Ajusta las proporciones */
}
```

### **Agregar Más Estadísticas**

Duplica un `.stat-box` en el HTML:

```html
<div class="stat-box">
    <div class="stat-label">Nueva Stat</div>
    <div class="stat-value">999</div>
</div>
```

---

## 🔧 Integración con stock-analyzer

Este overlay se integra perfectamente con tu proyecto `stock-analyzer`:

```python
# En TradingSystem o ManualPositionTracker
from update_overlay_stats import OverlayStatsUpdater

class TradingSystem:
    def __init__(self):
        self.overlay = OverlayStatsUpdater()

    def close_position(self, symbol):
        # ... tu código existente ...

        # Actualizar overlay automáticamente
        self.overlay.update_stats(
            realized_pl=self.total_realized_pnl,
            unrealized_pl=self.total_unrealized_pnl
        )
```

---

## 📊 Formato de Datos (stats.json)

```json
{
  "winStreak": 12,
  "realizedPL": 1247.50,
  "unrealizedPL": -328.75,
  "totalPL": 918.75,
  "metadata": {
    "lastUpdated": "2025-11-14T12:00:00Z",
    "totalTrades": 45,
    "winRate": 68.5
  }
}
```

---

## 🎥 Configuración de Streaming

| Plataforma | Resolución | FPS | Bitrate |
|------------|------------|-----|---------|
| **Twitch** | 1920x1080 | 60 | 6000 kbps |
| **YouTube** | 1920x1080 | 60 | 8000-12000 kbps |
| **Kick** | 1920x1080 | 60 | 8000 kbps |

---

## 🛠️ Comandos Útiles

```bash
# Ver estadísticas actuales
python update_overlay_stats.py --show

# Incrementar win streak
python update_overlay_stats.py --increment-streak

# Resetear win streak
python update_overlay_stats.py --reset-streak

# Actualizar todo
python update_overlay_stats.py \
  --win-streak 20 \
  --realized 2500.00 \
  --unrealized -150.00 \
  --total-trades 100 \
  --win-rate 75.5

# Ver ejemplos
python update_overlay_stats.py --example
```

---

## 🐛 Solución de Problemas

### **El overlay no se ve en OBS**
- ✅ Verifica que la ruta del HTML sea correcta
- ✅ Marca "Local file" en Browser Source
- ✅ Tamaño debe ser 1920x1080

### **Las animaciones se ven lentas**
- ✅ Activa aceleración por hardware en OBS
- ✅ Cierra otros programas pesados
- ✅ Reduce la complejidad de las animaciones en CSS

### **Las stats no se actualizan**
- ✅ Guarda el archivo stats.json después de editarlo
- ✅ Refresca la fuente Browser Source en OBS
- ✅ Marca "Refresh browser when scene becomes active"

### **El overlay tapa las ventanas**
- ✅ El overlay debe estar ARRIBA en la lista de fuentes
- ✅ Las capturas de pantalla deben estar DEBAJO

---

## 📚 Documentación

- **`OVERLAY_GUIDE.md`**: Guía completa paso a paso para configuración en OBS
- **`overlay_updater.js`**: Documentación de API JavaScript para updates
- **`update_overlay_stats.py`**: Ejemplos de integración con Python

---

## 🎯 Casos de Uso

### **1. Streamer de Trading + Gaming**
Muestra tu trading de BTC en vivo mientras juegas Pokémon TCG Pocket en tu iPhone.

### **2. Educador Financiero**
Enseña trading mientras entretienes con gaming, mostrando stats reales en tiempo real.

### **3. Dual Content Creator**
Crea contenido híbrido cripto-gaming con un overlay profesional que une ambos mundos.

---

## ⚠️ Aviso Legal

**Este overlay incluye el siguiente disclaimer:**

> ⚠️ NO ES CONSEJO DE INVERSIÓN · ENTRETENIMIENTO EDUCATIVO +18 · TRADE AT YOUR OWN RISK

**Asegúrate de:**
- Cumplir con las regulaciones de tu país sobre contenido de trading
- No dar consejos financieros no autorizados
- Incluir warnings apropiados sobre riesgos de inversión
- Cumplir con las políticas de la plataforma de streaming (Twitch, YouTube, etc.)

---

## 🤝 Contribuciones

Este overlay es parte del proyecto `stock-analyzer`. Para mejoras o personalizaciones:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Haz tus cambios
4. Submit un pull request

---

## 📝 Changelog

### **v1.0.0** - 2025-11-14
- ✅ Overlay inicial con diseño cripto-gaming
- ✅ Dos ventanas principales (vertical + horizontal)
- ✅ HUD dinámico con 4 estadísticas
- ✅ Animaciones de logos cripto y Pokémon
- ✅ Script Python para actualización automática
- ✅ Script JavaScript para updates en tiempo real
- ✅ Zona de webcam/logo
- ✅ Aviso legal incorporado

---

## 🚀 Roadmap

- [ ] Temas de color adicionales (Ethereum blue, Solana green)
- [ ] Panel de control web para actualizar stats
- [ ] Integración nativa con APIs de exchanges
- [ ] Alertas animadas para trades grandes
- [ ] Widgets adicionales (chat, donations, alerts)
- [ ] Exportación a PNG/GIF para redes sociales
- [ ] Modo vertical para TikTok/Instagram Reels

---

## 💬 Soporte

¿Problemas o preguntas?

1. Lee la guía completa: `OVERLAY_GUIDE.md`
2. Revisa los ejemplos en `update_overlay_stats.py`
3. Consulta la documentación de OBS Browser Source
4. Abre un issue en el repositorio

---

## 📄 Licencia

MIT License - Usa y modifica libremente para tus streams.

---

## 🎨 Créditos

- **Diseño**: Estilo cripto-gaming profesional
- **Fuentes**: Google Fonts (Orbitron, Rajdhani)
- **Paleta**: Bitcoin Orange (#F7931A), ETH Blue (#627EEA), SOL Green (#14F195)
- **Inspiración**: Estética tech/cyberpunk + branding cripto

---

## 🔥 ¡Haz tu stream destacar!

Con este overlay profesional, tu contenido cripto-gaming tendrá un aspecto único y memorable que cautivará a tu audiencia.

**¡Buena suerte con tus streams!** 🚀💰⚡

---

Made with 🧡 for the crypto-gaming community
