"""
Contexto corregido para Ollama con datos REALES y análisis del bug encontrado
"""

from datetime import datetime

def generate_corrected_context():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    context = f"""
# CONTEXTO CORREGIDO - ANALISIS REAL DE TRADING
Timestamp: {timestamp}

Eres un EXPERTO TRADER CUANTITATIVO. He identificado un BUG en el sistema y necesito tu análisis técnico.

## DATOS REALES CORREGIDOS (NO CONFUNDIR)

### TUS POSICIONES SHORT ACTUALES:
1. HP - Score REAL: 1.0 (cambio diario: +3.31%) - SHORT CORRECTO
   PnL: -$20.14 (-0.19%) - Perdiendo ligeramente
   
2. MOH - Score REAL: 1.5 (cambio diario: +3.55%) - SHORT CORRECTO  
   PnL: -$28.03 (-0.34%) - Perdiendo ligeramente
   
3. UNG - Score REAL: 2.5 (cambio diario: +2.03%) - SHORT EN EL LIMITE
   PnL: -$14.98 (-0.23%) - Perdiendo ligeramente
   
4. BRKR - Score: NO DISPONIBLE (no en watchlist) - ERROR DEL SISTEMA
   PnL: -$7.02 (-17.12%) - Perdiendo fuertemente

### ANALISIS TECNICO DE LAS DECISIONES:

DECISIONES CORRECTAS SEGUN CODIGO:
- HP (score 1.0): Muy por debajo threshold 2.5 para SHORT ✓
- MOH (score 1.5): Muy por debajo threshold 2.5 para SHORT ✓
- UNG (score 2.5): Exactamente en threshold 2.5 para SHORT (decisión límite)

DECISION INCORRECTA:
- BRKR: NO está en watchlist, NO debería haberse seleccionado

## BUG IDENTIFICADO EN EL CODIGO

### PROBLEMA: Historial de transacciones vacío

ARCHIVO: src/api/services/autotrader_service.py
LINEAS PROBLEMATICAS: 348-351 (compras) y 736-739 (shorts)

BUG EN CODIGO:
```python
# INCORRECTO (líneas 348-351):
INSERT INTO autotrader_transactions (symbol, action, quantity, price, reason)

# CORRECTO (según transaction_logger.py líneas 98-102):
INSERT INTO autotrader_transactions (symbol, action, quantity, price, timestamp, reason)
```

FALTA LA COLUMNA 'timestamp' en los INSERT statements!

### REGLAS DEL AUTOTRADER CONFIRMADAS:

COMPRA LONG: score >= 7.5 (línea 38)
VENTA LONG: score <= 4.0 (línea 39)
COMPRA SHORT STOCKS: score < 2.5 (línea 673)
COMPRA SHORT CRYPTO: score < 3.5 + confidence > 70% (líneas 272, 593)

## PREGUNTA ESPECIFICA PARA TU ANALISIS:

1. ¿Por qué mis posiciones SHORT están perdiendo dinero si los scores eran correctos para SHORT?
   - HP: score 1.0 (muy bearish) pero precio subió 3.31%
   - MOH: score 1.5 (muy bearish) pero precio subió 3.55%
   - UNG: score 2.5 (neutral-bearish) pero precio subió 2.03%

2. ¿El problema está en el timing? ¿Los scores predicen tendencia pero no el timing exacto?

3. ¿Debería ajustar los thresholds o es normal tener pérdidas temporales en SHORT positions correctamente seleccionadas?

4. ¿Cómo debería manejar BRKR que no está en watchlist pero de alguna forma se compró?

ANALIZA TECNICAMENTE: ¿El sistema de scoring está funcionando pero el market timing es el problema, o hay un error fundamental en la selección?

Dame tu análisis técnico de por qué scores bearish correctos están resultando en pérdidas temporales.
"""
    
    return context.strip()

def main():
    print("GENERANDO CONTEXTO CORREGIDO PARA OLLAMA...")
    
    context = generate_corrected_context()
    
    # Guardar archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_corrected_context_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(context)
    
    # Copiar al clipboard
    try:
        import pyperclip
        pyperclip.copy(context)
        print("SUCCESS: Contexto corregido copiado al clipboard!")
        print("-> Pega en Ollama con Ctrl+V")
    except ImportError:
        print("INFO: Para auto-copy: pip install pyperclip")
    
    print(f"Archivo: {filename}")
    print(f"Tamaño: {len(context):,} caracteres")
    print()
    print("NUEVA PREGUNTA PARA OLLAMA:")
    print("'Analiza por que mis scores bearish correctos estan resultando en perdidas temporales'")

if __name__ == "__main__":
    main()