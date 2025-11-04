# PupupuV3 Telegram Notifications Setup Guide

## Overview

The PupupuV3 scalping strategy includes automatic Telegram notifications when new trading signals are detected. This system sends detailed trade information including ML-predicted take profit levels to your Telegram group or chat.

---

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "PupupuV3 Trading Bot")
4. Choose a username for your bot (e.g., "pupupuv3_trading_bot")
5. **Copy the Bot Token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID

#### Option A: Private Chat
1. Search for **@userinfobot** in Telegram
2. Start a chat with it
3. It will show your **Chat ID** (e.g., `123456789`)

#### Option B: Group Chat
1. Create a new Telegram group
2. Add your bot to the group (search by username)
3. Add **@userinfobot** to the group
4. It will show the **Group Chat ID** (e.g., `-987654321`)
5. Remove @userinfobot from the group (optional)

**Alternative method:**
Run the provided script:
```bash
python get_group_chat_id.py
```

### 3. Configure Environment Variables

Add the following to your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Example:**
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-987654321
```

### 4. Test the Configuration

Run the API server:
```bash
python run_api.py
```

Check the startup logs for:
```
INFO - Telegram service initialized successfully
```

If you see:
```
WARNING - Telegram service disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID
```
Double-check your `.env` file configuration.

---

## Notification Types

### 1. Trade Signal Notification

Sent automatically when a **new valid signal** is detected via `/api/v1/pupupuv3/current-analysis` endpoint.

**Example Message:**

```
🟢 PUPUPUV3 SCALPING - COMPRA (LONG)

Símbolo: BTC/USDT
Entrada: $68,520.00
Stop Loss: $68,320.00
Riesgo: $600.00
Tamaño posición: 0.0875
🎯 ML Confidence: ALTA (81.5%)

🎯 TAKE PROFITS (Escalado)

TP1 (50% + move to BE): $68,720.00
   └─ R:R 1.00x

TP2 (30% exit): $69,120.00
   └─ R:R 8:1 | Prob: 72% | Tiempo: 2h

TP3 (20% exit): $70,320.00
   └─ R:R 14:1 | Prob: 51% | Tiempo: 4h

📋 CONDICIONES:
✅ Pivot Touch
✅ EMA(15) Test
✅ VWAP Alignment
✅ Volume Profile Support

2025-10-29 15:30:00
```

**Notification Trigger:**
- Only sent when a **NEW signal** is detected
- Duplicate prevention: Same signal won't be sent twice
- Requires ML model to be loaded for TP2/TP3 predictions

### 2. Trade Exit Notification

Sent when positions hit TP levels or stop loss (requires manual implementation in trading bot).

**Example Message:**

```
💰 PUPUPUV3 - GANANCIA

Símbolo: BTC/USDT
Dirección: LONG
🎯 (50%) Salida: TP1

Precio entrada: $68,520.00
Precio salida: $68,720.00

P&L (parcial): $300.00
R:R alcanzado: 1.00x
Posición restante: 50%

2025-10-29 16:00:00
```

---

## How It Works

### Signal Detection Flow

```
Frontend/Scheduler polls → /api/v1/pupupuv3/current-analysis
                              ↓
                      Analyze market data
                              ↓
                      Signal detected?
                              ↓ (YES)
                      ML predicts TP2/TP3
                              ↓
                      Check if signal is NEW
                              ↓ (YES - not notified before)
                      Send Telegram notification
                              ↓
                      Mark signal as notified
                              ↓
                      Return response to frontend
```

### Duplicate Prevention

The system uses a **signal tracking dictionary**:

```python
last_notified_signal = {
    'BTC/USDT': 'BTC/USDT_1698589800000_LONG',
    'ETH/USDT': 'ETH/USDT_1698589900000_SHORT'
}
```

**Signal ID Format:**
```
{symbol}_{timestamp}_{direction}
```

This ensures:
- Same signal isn't sent multiple times
- Different signals (new timestamp or direction) trigger new notifications
- Per-symbol tracking (BTC signal doesn't block ETH signal)

---

## API Integration

### Automatic Notifications

The `/current-analysis` endpoint automatically sends Telegram notifications when:

1. ✅ A valid signal is detected (`signal.is_valid == True`)
2. ✅ ML model is loaded and makes predictions
3. ✅ Signal is NEW (hasn't been notified before)

**No manual intervention required!**

### Polling Strategy

To receive real-time notifications, poll the endpoint regularly:

**JavaScript Example:**
```javascript
const pollInterval = 60000; // 60 seconds

setInterval(async () => {
  const response = await fetch('http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT');
  const data = await response.json();

  if (data.signal) {
    console.log('Signal detected:', data.signal);
    console.log('ML prediction:', data.ml_prediction);
    // Telegram notification sent automatically by backend
  }
}, pollInterval);
```

**Python Example (Background Scheduler):**
```python
import schedule
import time
import requests

def check_signals():
    response = requests.get('http://localhost:8000/api/v1/pupupuv3/current-analysis?symbol=BTC/USDT')
    data = response.json()

    if data.get('signal'):
        print(f"Signal detected: {data['signal']['direction']} at {data['signal']['entry']}")
        # Telegram notification sent automatically

schedule.every(1).minutes.do(check_signals)

while True:
    schedule.run_pending()
    time.sleep(1)
```

---

## Manual Notification Methods

### Send Custom Trade Notification

```python
from src.api.services.telegram_service import telegram_service

telegram_service.send_pupupuv3_trade_notification(
    symbol="BTC/USDT",
    direction="LONG",
    entry_price=68520.00,
    stop_loss=68320.00,
    tp1=68720.00,
    tp2_price=69120.00,
    tp2_ratio=8.0,
    tp2_probability=0.72,
    tp2_timeframe="2h",
    tp3_price=70320.00,
    tp3_ratio=14.0,
    tp3_probability=0.51,
    tp3_timeframe="4h",
    risk_amount=600.00,
    position_size=0.0875,
    ml_confidence=0.815,
    conditions_met={
        'touch': True,
        'ema_test': True,
        'vwap_alignment': True,
        'volume_profile_support': True
    }
)
```

### Send Exit Notification

```python
from src.api.services.telegram_service import telegram_service

telegram_service.send_pupupuv3_exit_notification(
    symbol="BTC/USDT",
    direction="LONG",
    entry_price=68520.00,
    exit_price=68720.00,
    exit_level="TP1",
    pnl=300.00,
    percentage_remaining=50.0,
    rr_achieved=1.0
)
```

---

## Notification Customization

### ML Confidence Levels

The system automatically categorizes ML confidence:

| Confidence Score | Level | Emoji |
|------------------|-------|-------|
| ≥ 80% | ALTA | 🎯 |
| 70-79% | MEDIA | ⚡ |
| < 70% | BAJA | ⚠️ |

### Exit Level Emojis

| Exit Level | Emoji | Description |
|------------|-------|-------------|
| TP1 | 🎯 (50%) | First take profit |
| TP2 | 🎯🎯 (30%) | Second take profit |
| TP3 | 🎯🎯🎯 (20%) | Third take profit |
| STOP_LOSS | 🛑 | Stop loss hit |
| BREAK_EVEN | 🟰 | Moved to breakeven |
| MANUAL | 👤 | Manual exit |

---

## Troubleshooting

### No Notifications Received

**Check 1: Telegram Service Status**
```python
from src.api.services.telegram_service import telegram_service

print(f"Telegram enabled: {telegram_service.enabled}")
print(f"Bot token: {telegram_service.bot_token[:10]}...")
print(f"Chat ID: {telegram_service.chat_id}")
```

**Check 2: Test Manual Message**
```python
from src.api.services.telegram_service import telegram_service

result = telegram_service.send_message("🧪 Test message from PupupuV3")
print(f"Message sent: {result}")
```

**Check 3: Verify Environment Variables**
```bash
# Linux/Mac
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# Windows
echo %TELEGRAM_BOT_TOKEN%
echo %TELEGRAM_CHAT_ID%
```

### Duplicate Notifications

If you're receiving duplicate notifications:

1. **Check polling frequency** - Don't poll faster than signal generation
2. **Restart API server** - Clears the `last_notified_signal` cache
3. **Check multiple instances** - Ensure only one API server is running

### Wrong Chat Receiving Messages

- Verify `TELEGRAM_CHAT_ID` is correct
- For groups, ensure chat ID starts with `-` (e.g., `-987654321`)
- For private chats, use positive number (e.g., `123456789`)

### Bot Not Responding

1. **Check bot is started** - Send `/start` to your bot in Telegram
2. **For groups** - Ensure bot has "Send Messages" permission
3. **Verify bot token** - Try creating a new bot and updating token

---

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Keep bot token secret** - It provides full access to your bot
3. **Restrict bot permissions** - Only give necessary permissions
4. **Use private groups** - For sensitive trading information
5. **Rotate tokens periodically** - Generate new bot token every 3-6 months

---

## Advanced: Background Scheduler Integration

To run continuous monitoring with automatic Telegram alerts:

**Create:** `pupupuv3_monitor.py`
```python
import schedule
import time
import requests
from datetime import datetime

API_URL = "http://localhost:8000/api/v1/pupupuv3/current-analysis"
SYMBOL = "BTC/USDT"

def monitor_signals():
    try:
        response = requests.get(f"{API_URL}?symbol={SYMBOL}", timeout=10)
        data = response.json()

        if data.get('signal'):
            signal = data['signal']
            ml = data.get('ml_prediction', {})

            print(f"[{datetime.now()}] Signal detected:")
            print(f"  {signal['direction']} at ${signal['entry']}")
            print(f"  TP2: ${ml.get('tp2_price', 'N/A')} ({ml.get('tp2_probability', 0):.0f}%)")
            print(f"  TP3: ${ml.get('tp3_price', 'N/A')} ({ml.get('tp3_probability', 0):.0f}%)")
            # Telegram notification sent automatically by API
        else:
            print(f"[{datetime.now()}] No signal - waiting...")

    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}")

# Run every minute
schedule.every(1).minutes.do(monitor_signals)

print(f"🚀 PupupuV3 Monitor started for {SYMBOL}")
print("📊 Checking for signals every minute...")
print("📱 Telegram notifications enabled\n")

while True:
    schedule.run_pending()
    time.sleep(1)
```

**Run:**
```bash
python pupupuv3_monitor.py
```

---

## Message Templates

### Trade Opened (LONG Example)
```
🟢 PUPUPUV3 SCALPING - COMPRA (LONG)
Símbolo: BTC/USDT
Entrada: $68,520.00
Stop Loss: $68,320.00
Riesgo: $600.00
🎯 ML Confidence: ALTA (81.5%)
```

### Trade Opened (SHORT Example)
```
🔴 PUPUPUV3 SCALPING - VENTA (SHORT)
Símbolo: ETH/USDT
Entrada: $2,450.00
Stop Loss: $2,500.00
Riesgo: $300.00
⚡ ML Confidence: MEDIA (74.2%)
```

### TP1 Hit (50% Exit + BE)
```
💰 PUPUPUV3 - GANANCIA
Símbolo: BTC/USDT
🎯 (50%) Salida: TP1
P&L (parcial): $300.00
Posición restante: 50%
```

### TP2 Hit (30% Exit)
```
💰 PUPUPUV3 - GANANCIA
Símbolo: BTC/USDT
🎯🎯 (30%) Salida: TP2
P&L (parcial): $720.00
Posición restante: 20%
```

### Stop Loss Hit
```
🛑 PUPUPUV3 - PÉRDIDA
Símbolo: BTC/USDT
🛑 Salida: STOP_LOSS
P&L (parcial): -$600.00
Posición restante: 0%
```

---

## Summary

✅ **Automatic notifications** when signals are detected
✅ **ML predictions** included (TP2/TP3 with probabilities)
✅ **Duplicate prevention** - Same signal won't spam
✅ **Multi-symbol support** - Track multiple pairs
✅ **Detailed trade info** - Entry, SL, TPs, conditions
✅ **Exit tracking** - Partial closes and final exits

The PupupuV3 Telegram integration provides real-time trading alerts with ML-enhanced take profit predictions, enabling you to execute trades confidently with data-driven targets.
