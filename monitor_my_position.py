"""
Monitor My Position - Real-Time Exit Signal

Monitorea tu posición actual y te dice CUANDO VENDER basado en señales ML.
Actualiza cada 15 minutos automáticamente.

Uso:
    python monitor_my_position.py

    # O especificar manualmente
    python monitor_my_position.py --market NDX --entry 23670.50 --stop 23655.50
"""

import requests
import time
import argparse
from datetime import datetime, timedelta
import os
from typing import Optional, Dict

# API Configuration
API_BASE = "http://localhost:8000/api/v1/box-strategy"


class PositionMonitor:
    """Monitor de posición en tiempo real"""

    def __init__(self, trade_data: Dict):
        self.trade = trade_data
        self.last_signal = None
        self.alert_shown = False

    def get_current_price(self) -> float:
        """Obtiene precio actual del mercado"""
        try:
            response = requests.get(f"{API_BASE}/market/{self.trade['market']}")
            response.raise_for_status()
            data = response.json()

            if data.get('box_setup') and data['box_setup'].get('current_price'):
                return data['box_setup']['current_price']

            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo precio: {e}")
            return None

    def get_exit_signal(self) -> Optional[Dict]:
        """Obtiene señal de exit del API"""
        try:
            response = requests.post(
                f"{API_BASE}/exit-signal",
                json=self.trade,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError:
            print("❌ ERROR: API no disponible. Ejecuta: python run_api.py")
            return None
        except Exception as e:
            print(f"⚠️  Error obteniendo señal: {e}")
            return None

    def calculate_pnl(self, current_price: float) -> tuple:
        """Calcula P&L actual"""
        entry = self.trade['entry_price']
        stop = self.trade['stop_loss']

        if self.trade['direction'] == 'LONG':
            pnl_points = current_price - entry
            risk = entry - stop
        else:  # SHORT
            pnl_points = entry - current_price
            risk = stop - entry

        pnl_r = pnl_points / risk if risk > 0 else 0
        pnl_pct = (pnl_points / entry) * 100

        return pnl_points, pnl_r, pnl_pct

    def display_status(self, signal: Dict, iteration: int):
        """Muestra estado actual de la posición"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        current_price = signal['current_price']
        pnl_points, pnl_r, pnl_pct = self.calculate_pnl(current_price)

        # Header
        print("\n" + "="*90)
        print(" "*25 + "🎯 MONITOR DE POSICIÓN EN TIEMPO REAL")
        print("="*90 + "\n")

        print(f"Update #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"Próxima actualización en 15 minutos...\n")

        # Trade Info
        print("─"*90)
        print("INFORMACIÓN DEL TRADE")
        print("─"*90)

        print(f"Mercado:          {self.trade['market']}")
        print(f"Dirección:        {self.trade['direction']}")
        print(f"Entry:            {self.trade['entry_price']:.2f}")
        print(f"Stop Loss:        {self.trade['stop_loss']:.2f}")
        print(f"Precio Actual:    {current_price:.2f}")

        # P&L
        print("\n" + "─"*90)
        print("PROFIT & LOSS")
        print("─"*90)

        pnl_color = "🟢" if pnl_points > 0 else "🔴" if pnl_points < 0 else "⚪"
        print(f"{pnl_color} P&L:             {pnl_points:+.2f} puntos ({pnl_pct:+.2f}%)")
        print(f"{pnl_color} P&L en R:         {pnl_r:+.2f}R")

        # Target Progress
        tp1_reached = "✅" if pnl_r >= 0.9 else "⏳"
        tp2_reached = "✅" if pnl_r >= 1.9 else "⏳"
        tp3_reached = "✅" if pnl_r >= 2.9 else "⏳"

        print(f"\n{tp1_reached} TP1 (1R):         {self.trade['tp1']:.2f}")
        print(f"{tp2_reached} TP2 (2R):         {self.trade['tp2']:.2f}")
        print(f"{tp3_reached} TP3 (3R):         {self.trade['tp3']:.2f}")

        # Exit Signal Analysis
        print("\n" + "="*90)
        print("ANÁLISIS DE SEÑALES DE SALIDA")
        print("="*90 + "\n")

        # Exhaustion Signal
        exhaustion_emoji = {
            "STRONG": "🔴",
            "MODERATE": "🟡",
            "WEAK": "🟠",
            "NONE": "🟢"
        }
        ex_emoji = exhaustion_emoji.get(signal['exhaustion_signal'], "⚪")

        print(f"{ex_emoji} Señal de Agotamiento:  {signal['exhaustion_signal']}")

        # RSI Divergence
        rsi_score = signal['rsi_divergence_15min']
        rsi_type = signal['rsi_divergence_type']

        if abs(rsi_score) > 0.7:
            rsi_emoji = "🔴"
        elif abs(rsi_score) > 0.3:
            rsi_emoji = "🟡"
        else:
            rsi_emoji = "🟢"

        print(f"{rsi_emoji} RSI Divergencia:       {rsi_type}")
        print(f"   Score:              {rsi_score:.3f}")

        # Momentum
        mom_emoji = "🔴" if signal['momentum_weakening'] else "🟢"
        mom_status = "DEBILITÁNDOSE" if signal['momentum_weakening'] else "FUERTE"
        print(f"{mom_emoji} Momentum:              {mom_status}")

        # Next TP Info
        print(f"\n📊 Próximo Objetivo:     {signal['next_tp_name']} @ {signal['next_tp_level']:.2f}")
        print(f"   Distancia:           {signal['distance_to_next_tp_r']:.2f}R")
        print(f"   Probabilidad:        {signal['next_tp_probability']*100:.1f}%")
        print(f"   Confianza ML:        {signal['confidence']*100:.1f}%")

        # RECOMMENDATION (BIG)
        print("\n" + "="*90)
        print("🚨 RECOMENDACIÓN DE ACCIÓN")
        print("="*90 + "\n")

        action = signal['recommended_action']

        if action == "CLOSE_NOW":
            print("╔" + "═"*88 + "╗")
            print("║" + " "*88 + "║")
            print("║" + " "*20 + "🔴 VENDER AHORA - SALIR INMEDIATAMENTE" + " "*29 + "║")
            print("║" + " "*88 + "║")
            print("╚" + "═"*88 + "╝")

            print("\n⚠️  RAZÓN:")
            print(f"   {signal['analysis']['recommendation_reasoning']}")

            print("\n✅ ACCIÓN SUGERIDA:")
            print(f"   1. Cerrar posición AL MERCADO")
            print(f"   2. Asegurar profit de {pnl_r:.2f}R ({pnl_points:+.2f} puntos)")
            print(f"   3. No esperar - Alto riesgo de reversión")

            # Alert sound/notification
            if not self.alert_shown:
                print("\n" + "🔔"*45)
                print("\a")  # Beep
                self.alert_shown = True

        elif action == "TRAIL_STOP":
            print("╔" + "═"*88 + "╗")
            print("║" + " "*88 + "║")
            print("║" + " "*18 + "🟡 ACTIVAR TRAILING STOP - PROTEGER PROFIT" + " "*27 + "║")
            print("║" + " "*88 + "║")
            print("╚" + "═"*88 + "╝")

            print("\n⚠️  RAZÓN:")
            print(f"   {signal['analysis']['recommendation_reasoning']}")

            # Calculate trailing stop suggestion
            if self.trade['direction'] == 'LONG':
                trail_stop = current_price - (current_price - entry) * 0.3  # Protect 70% of profit
            else:
                trail_stop = current_price + (entry - current_price) * 0.3

            print("\n✅ ACCIÓN SUGERIDA:")
            print(f"   1. Mover Stop Loss a: {trail_stop:.2f}")
            print(f"   2. Proteger profit de {pnl_r*0.7:.2f}R mínimo")
            print(f"   3. Dejar correr si continúa favorable")

        else:  # HOLD
            print("╔" + "═"*88 + "╗")
            print("║" + " "*88 + "║")
            print("║" + " "*22 + "🟢 MANTENER POSICIÓN - ESPERAR " + signal['next_tp_name'] + " "*22 + "║")
            print("║" + " "*88 + "║")
            print("╚" + "═"*88 + "╝")

            print("\n✅ RAZÓN:")
            print(f"   {signal['analysis']['recommendation_reasoning']}")

            print("\n📈 CONTINUAR:")
            print(f"   1. Sin señales de agotamiento significativas")
            print(f"   2. {signal['next_tp_probability']*100:.0f}% probabilidad de alcanzar {signal['next_tp_name']}")
            print(f"   3. Target: {signal['next_tp_level']:.2f}")

        # Detailed Analysis
        print("\n" + "─"*90)
        print("ANÁLISIS DETALLADO")
        print("─"*90 + "\n")

        print("RSI Analysis:")
        print(f"  {signal['analysis']['rsi_analysis']['interpretation']}")

        print("\nMomentum Analysis:")
        print(f"  {signal['analysis']['momentum_analysis']['interpretation']}")

        print("\nExhaustion Analysis:")
        print(f"  {signal['analysis']['exhaustion_analysis']['interpretation']}")

        print("\n" + "="*90)

        # Save to log
        self.log_signal(signal, iteration)

    def log_signal(self, signal: Dict, iteration: int):
        """Guarda señales en log file"""
        log_file = "position_monitor.log"

        with open(log_file, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"\n[{timestamp}] Update #{iteration}\n")
            f.write(f"Price: {signal['current_price']:.2f} | ")
            f.write(f"P&L: {signal['current_pnl_r']:.2f}R | ")
            f.write(f"Action: {signal['recommended_action']} | ")
            f.write(f"Exhaustion: {signal['exhaustion_signal']} | ")
            f.write(f"RSI Div: {signal['rsi_divergence_15min']:.3f}\n")

    def monitor_loop(self, check_interval: int = 900):
        """
        Loop principal de monitoreo

        Args:
            check_interval: Segundos entre checks (default: 900 = 15 min)
        """
        print("\n🚀 Iniciando monitor de posición...")
        print(f"📊 Mercado: {self.trade['market']}")
        print(f"📈 Dirección: {self.trade['direction']}")
        print(f"💰 Entry: {self.trade['entry_price']:.2f}")
        print(f"\n⏱️  Actualizando cada {check_interval // 60} minutos")
        print("⌨️  Presiona Ctrl+C para salir\n")

        iteration = 0

        try:
            while True:
                iteration += 1

                # Get exit signal
                signal = self.get_exit_signal()

                if signal:
                    self.display_status(signal, iteration)

                    # Store for comparison
                    self.last_signal = signal

                    # If CLOSE_NOW, ask for confirmation to continue monitoring
                    if signal['recommended_action'] == 'CLOSE_NOW':
                        print("\n❓ ¿Continuar monitoreando? (presiona Ctrl+C para salir)")

                else:
                    print(f"\n⚠️  No se pudo obtener señal. Reintentando en {check_interval // 60} min...")

                # Wait for next check
                if iteration == 1:
                    print(f"\n⏳ Esperando {check_interval // 60} minutos hasta próxima actualización...")

                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n👋 Monitor detenido por usuario")
            print(f"📝 Log guardado en: position_monitor.log")


def main():
    parser = argparse.ArgumentParser(
        description='Monitor tu posición actual y recibe señales de exit en tiempo real'
    )

    parser.add_argument('--market', default='NDX', help='Market code (default: NDX)')
    parser.add_argument('--entry', type=float, help='Entry price')
    parser.add_argument('--stop', type=float, help='Stop loss')
    parser.add_argument('--direction', default='LONG', choices=['LONG', 'SHORT'])
    parser.add_argument('--interval', type=int, default=15, help='Check interval in minutes (default: 15)')

    args = parser.parse_args()

    # Si no se proporcionan entry/stop, usar valores del trade de hoy (NDX ejemplo)
    if args.entry is None:
        print("\n📝 Usando datos del trade de ejemplo...")
        print("   (Puedes especificar con --entry y --stop)")

        # Ejemplo NDX - ajusta estos valores al trade real
        trade_data = {
            "market": args.market,
            "direction": args.direction,
            "entry_price": 21050.0 if args.entry is None else args.entry,
            "entry_time": datetime.now().replace(hour=10, minute=5).isoformat(),
            "stop_loss": 21035.0 if args.stop is None else args.stop,
            "tp1": 21065.0,
            "tp2": 21080.0,
            "tp3": 21095.0
        }

        print(f"\n   Market: {trade_data['market']}")
        print(f"   Entry: {trade_data['entry_price']}")
        print(f"   Stop: {trade_data['stop_loss']}")

        response = input("\n¿Continuar con estos valores? (y/n): ")
        if response.lower() != 'y':
            print("\nEspecifica tu trade con:")
            print("  python monitor_my_position.py --market NDX --entry 21050 --stop 21035")
            return

    else:
        # Calcular TPs basados en risk
        risk = abs(args.entry - args.stop)

        if args.direction == 'LONG':
            tp1 = args.entry + (1.0 * risk)
            tp2 = args.entry + (2.0 * risk)
            tp3 = args.entry + (3.0 * risk)
        else:
            tp1 = args.entry - (1.0 * risk)
            tp2 = args.entry - (2.0 * risk)
            tp3 = args.entry - (3.0 * risk)

        trade_data = {
            "market": args.market,
            "direction": args.direction,
            "entry_price": args.entry,
            "entry_time": datetime.now().replace(hour=10, minute=5).isoformat(),
            "stop_loss": args.stop,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3
        }

    # Initialize monitor
    monitor = PositionMonitor(trade_data)

    # Start monitoring
    monitor.monitor_loop(check_interval=args.interval * 60)


if __name__ == "__main__":
    main()
