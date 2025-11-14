# 🎮 Guía de Uso - Crypto Gaming Stream Overlay

## 📋 Descripción

Overlay profesional 1920x1080 para streaming con estética cripto-gaming, diseñado para mostrar simultáneamente:
- **Pokémon TCG Pocket** (captura de iPhone en formato vertical)
- **Trading de BTC** (plataforma de trading en formato horizontal)
- **HUD de estadísticas** en tiempo real
- **Zona de webcam/logo**
- **Elementos animados** (logos cripto y decoraciones Pokémon)

---

## 🚀 Configuración en OBS Studio

### **Paso 1: Abrir OBS y crear una nueva escena**

1. Abre **OBS Studio**
2. Crea una nueva escena: `Crypto Gaming Stream`
3. Establece la resolución de salida: **1920x1080**
   - Ve a `Archivo` → `Configuración` → `Vídeo`
   - Resolución de salida: `1920x1080`

---

### **Paso 2: Agregar el Overlay como Browser Source**

1. En tu escena, haz clic en el botón **`+`** en la sección de Fuentes
2. Selecciona **`Navegador`** (Browser Source)
3. Nombra la fuente: `Overlay Principal`
4. Configura los siguientes parámetros:

   ```
   ☑️ Local file
   Archivo: [Ruta a tu archivo stream_overlay.html]

   Ancho: 1920
   Alto: 1080

   ☑️ Shutdown source when not visible
   ☑️ Refresh browser when scene becomes active
   ```

5. Haz clic en **OK**

---

### **Paso 3: Agregar captura de pantalla del iPhone (Pokémon TCG Pocket)**

**Opción A - Usando captura de pantalla de iOS:**

1. Agrega una nueva fuente: **`Captura de ventana`** o **`Captura de dispositivo de vídeo`**
2. Selecciona tu iPhone (conectado via QuickTime, NDI, o software de captura)
3. **Posición y escala:**
   - **X:** `20px`
   - **Y:** `60px`
   - **Ancho:** `~605px`
   - **Alto:** `~880px`

4. Arrastra esta fuente **DEBAJO** del overlay en la lista de fuentes (para que quede dentro del marco)

**Opción B - Usando iPhone como cámara (iOS 16+):**

1. Conecta tu iPhone al Mac/PC via Continuity Camera
2. Agrega fuente: **`Dispositivo de captura de vídeo`**
3. Selecciona tu iPhone
4. Ajusta posición y tamaño como arriba

---

### **Paso 4: Agregar captura de la plataforma de trading**

1. Agrega una nueva fuente: **`Captura de ventana`**
2. Selecciona tu navegador o aplicación de trading (Binance, TradingView, etc.)
3. **Posición y escala:**
   - **X:** `~645px`
   - **Y:** `60px`
   - **Ancho:** `~1255px`
   - **Alto:** `~880px`

4. Coloca esta fuente **DEBAJO** del overlay en la lista

---

### **Paso 5: Agregar Webcam**

1. Agrega una nueva fuente: **`Dispositivo de captura de vídeo`**
2. Selecciona tu webcam
3. **Posición:**
   - **X:** `1570px`
   - **Y:** `720px`
   - **Ancho:** `320px`
   - **Alto:** `180px`

4. Coloca esta fuente **DEBAJO** del overlay

---

## 🎨 Personalización del Overlay

### **Editar estadísticas en tiempo real:**

Abre el archivo `stream_overlay.html` y busca la sección del HUD:

```html
<div class="stat-box">
    <div class="stat-label">Racha de Victorias</div>
    <div class="stat-value">12</div>  <!-- Cambia este valor -->
</div>
```

### **Actualizar estadísticas dinámicamente:**

El overlay incluye un script JavaScript comentado que puedes habilitar para actualizar los valores automáticamente.

**Opción 1 - Actualización manual:**
- Edita los valores HTML directamente
- Refresca la fuente Browser Source en OBS (clic derecho → Actualizar)

**Opción 2 - Actualización automática desde archivo JSON:**

Crea un archivo `stats.json` con este formato:

```json
{
  "winStreak": 15,
  "realizedPL": 1247.50,
  "unrealizedPL": -328.75,
  "totalPL": 918.75
}
```

Luego modifica el script en el HTML para leer este archivo (requiere servidor local o usar OBS Browser Source con permisos de archivo).

**Opción 3 - Conectar a tu bot/API:**
- Si tienes un bot de trading, puedes hacer que actualice los valores via WebSocket o API REST
- Modifica la función `updateStats()` en el script

---

## 🎯 Orden de Capas en OBS (de arriba a abajo)

Para que todo funcione correctamente, el orden de las fuentes debe ser:

```
1. 🔝 Overlay Principal (Browser Source) - stream_overlay.html
2. 📱 Captura iPhone (Pokémon)
3. 💹 Captura Trading Platform
4. 📷 Webcam
5. 🎨 Fondo (opcional, puede ser color sólido o imagen)
```

**Importante:** El overlay debe estar **arriba de todo** para que los marcos, HUD y efectos se vean correctamente.

---

## 🎬 Exportar como PNG (Alternativa)

Si prefieres usar el overlay como imagen PNG estática (sin animaciones):

1. **Opción A - Screenshot desde navegador:**
   - Abre `stream_overlay.html` en Google Chrome
   - Presiona `F12` → Consola
   - Cambia el tamaño de la ventana del navegador a exactamente 1920x1080
   - Usa una extensión como "GoFullPage" o "Awesome Screenshot" para capturar
   - O usa la herramienta de screenshot del navegador

2. **Opción B - Usando Puppeteer (Node.js):**
   ```javascript
   const puppeteer = require('puppeteer');

   (async () => {
     const browser = await puppeteer.launch();
     const page = await browser.newPage();
     await page.setViewport({ width: 1920, height: 1080 });
     await page.goto('file:///ruta/a/stream_overlay.html');
     await page.screenshot({ path: 'overlay.png', omitBackground: true });
     await browser.close();
   })();
   ```

---

## 🔧 Ajustes y Tips

### **Cambiar colores:**

Busca en el CSS estas variables:
- **Naranja Bitcoin:** `#F7931A`
- **Verde (ganancias):** `#14F195`
- **Rojo (pérdidas):** `#FF4444`
- **Ethereum azul:** `#627EEA`
- **Solana verde:** `#14F195`

### **Modificar tamaños de ventanas:**

En el CSS, ajusta las proporciones del grid:

```css
.overlay-container {
    grid-template-columns: 1fr 2fr;  /* 1fr = ventana A, 2fr = ventana B */
}
```

### **Deshabilitar animaciones:**

Si las animaciones consumen muchos recursos, comenta estas secciones en el CSS:
- `@keyframes float`
- `@keyframes walk`
- `@keyframes pulse`

### **Añadir más estadísticas:**

Duplica un `.stat-box` en el HTML y edita el contenido:

```html
<div class="stat-box">
    <div class="stat-label">Nueva Estadística</div>
    <div class="stat-value">999</div>
</div>
```

---

## 📱 Usar con Stream Deck

Si tienes un Elgato Stream Deck, puedes:

1. **Crear botones para cambiar escenas**
2. **Actualizar estadísticas** via archivos de texto que el overlay lee
3. **Activar/desactivar** elementos del overlay

---

## 🐛 Solución de Problemas

### **El overlay no se ve:**
- ✅ Verifica que la ruta del archivo HTML sea correcta
- ✅ Asegúrate de que Browser Source tenga ancho/alto 1920x1080
- ✅ Comprueba que "Local file" esté marcado

### **Las animaciones no funcionan:**
- ✅ Refresca la fuente Browser Source
- ✅ Verifica que OBS esté usando hardware acceleration
- ✅ Cierra otros programas pesados

### **Las estadísticas no se actualizan:**
- ✅ Edita el HTML y guarda cambios
- ✅ Haz clic derecho en Browser Source → "Actualizar"
- ✅ O marca "Refresh browser when scene becomes active"

### **El overlay tapa las ventanas:**
- ✅ Verifica el orden de las capas (overlay debe estar arriba)
- ✅ Ajusta las posiciones X/Y de las capturas de pantalla

---

## 🎥 Streaming en Plataformas

### **Twitch:**
- Resolución recomendada: 1920x1080 @ 60fps
- Bitrate: 6000 kbps

### **YouTube:**
- Resolución: 1920x1080 @ 60fps
- Bitrate: 8000-12000 kbps

### **Kick:**
- Resolución: 1920x1080 @ 60fps
- Bitrate: 8000 kbps

---

## 📞 Soporte

Si tienes problemas o quieres personalizar aún más el overlay:
- Edita el archivo HTML/CSS directamente
- Usa la consola del navegador (F12) para debuggear
- Consulta la documentación de OBS Browser Source

---

## ⚖️ Aviso Legal

Este overlay incluye el disclaimer:

**"⚠️ NO ES CONSEJO DE INVERSIÓN · ENTRETENIMIENTO EDUCATIVO +18 · TRADE AT YOUR OWN RISK"**

Asegúrate de cumplir con las regulaciones de tu país respecto a contenido de trading y juegos de azar.

---

## 🎨 Créditos

- **Fuentes:** Google Fonts (Orbitron, Rajdhani)
- **Diseño:** Estilo cripto-gaming profesional
- **Paleta:** Bitcoin Orange (#F7931A)

---

¡Disfruta de tu stream! 🚀💰⚡
