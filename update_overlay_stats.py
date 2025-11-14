#!/usr/bin/env python3
"""
Script para actualizar las estadísticas del overlay de streaming
Integrable con sistemas de trading automáticos

Uso:
    python update_overlay_stats.py --win-streak 15 --realized 1247.50 --unrealized -328.75

O importar como módulo:
    from update_overlay_stats import update_stats
    update_stats(win_streak=15, realized_pl=1247.50, unrealized_pl=-328.75)
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path


class OverlayStatsUpdater:
    """Gestor de actualización de estadísticas del overlay"""

    def __init__(self, stats_file='stats.json'):
        self.stats_file = Path(__file__).parent / stats_file

    def load_stats(self):
        """Cargar estadísticas actuales"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._get_default_stats()

    def _get_default_stats(self):
        """Estadísticas por defecto"""
        return {
            "winStreak": 0,
            "realizedPL": 0.0,
            "unrealizedPL": 0.0,
            "totalPL": 0.0,
            "metadata": {
                "lastUpdated": datetime.utcnow().isoformat() + "Z",
                "streamStartTime": datetime.utcnow().isoformat() + "Z",
                "totalTrades": 0,
                "winRate": 0.0
            }
        }

    def update_stats(self, win_streak=None, realized_pl=None, unrealized_pl=None,
                    total_trades=None, win_rate=None):
        """
        Actualizar estadísticas del overlay

        Args:
            win_streak (int): Racha de victorias actual
            realized_pl (float): P/L realizado
            unrealized_pl (float): P/L no realizado
            total_trades (int): Total de trades realizados
            win_rate (float): Porcentaje de win rate
        """
        stats = self.load_stats()

        # Actualizar valores si se proporcionan
        if win_streak is not None:
            stats["winStreak"] = int(win_streak)

        if realized_pl is not None:
            stats["realizedPL"] = float(realized_pl)

        if unrealized_pl is not None:
            stats["unrealizedPL"] = float(unrealized_pl)

        # Calcular total P/L
        stats["totalPL"] = stats["realizedPL"] + stats["unrealizedPL"]

        # Actualizar metadata
        stats["metadata"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

        if total_trades is not None:
            stats["metadata"]["totalTrades"] = int(total_trades)

        if win_rate is not None:
            stats["metadata"]["winRate"] = float(win_rate)

        # Guardar archivo
        self.save_stats(stats)

        return stats

    def save_stats(self, stats):
        """Guardar estadísticas en archivo JSON"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

    def increment_win_streak(self):
        """Incrementar racha de victorias en 1"""
        stats = self.load_stats()
        stats["winStreak"] += 1
        stats["metadata"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        self.save_stats(stats)
        return stats["winStreak"]

    def reset_win_streak(self):
        """Resetear racha de victorias a 0"""
        stats = self.load_stats()
        stats["winStreak"] = 0
        stats["metadata"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        self.save_stats(stats)
        return 0

    def get_current_stats(self):
        """Obtener estadísticas actuales"""
        return self.load_stats()


# ============================================
# INTEGRACIÓN CON SISTEMA DE TRADING
# ============================================

def integrate_with_trading_bot():
    """
    Ejemplo de integración con un bot de trading

    Conecta este script con tu sistema de trading para actualizar
    las estadísticas automáticamente después de cada trade
    """
    updater = OverlayStatsUpdater()

    # Ejemplo: Después de un trade exitoso
    def on_trade_completed(trade_result):
        """Callback cuando se completa un trade"""
        if trade_result['status'] == 'win':
            updater.increment_win_streak()
        else:
            updater.reset_win_streak()

        # Actualizar P/L
        updater.update_stats(
            realized_pl=trade_result.get('realized_pl'),
            unrealized_pl=trade_result.get('unrealized_pl'),
            total_trades=trade_result.get('total_trades'),
            win_rate=trade_result.get('win_rate')
        )

    return on_trade_completed


# ============================================
# EJEMPLOS DE USO
# ============================================

def example_usage():
    """Ejemplos de cómo usar el updater"""

    updater = OverlayStatsUpdater()

    # Ejemplo 1: Actualización simple
    print("Ejemplo 1: Actualización simple")
    stats = updater.update_stats(
        win_streak=15,
        realized_pl=1247.50,
        unrealized_pl=-328.75
    )
    print(f"Stats actualizadas: {json.dumps(stats, indent=2)}\n")

    # Ejemplo 2: Incrementar win streak
    print("Ejemplo 2: Incrementar win streak")
    new_streak = updater.increment_win_streak()
    print(f"Nueva racha: {new_streak}\n")

    # Ejemplo 3: Obtener stats actuales
    print("Ejemplo 3: Stats actuales")
    current = updater.get_current_stats()
    print(f"Win Streak: {current['winStreak']}")
    print(f"Realized P/L: ${current['realizedPL']:.2f}")
    print(f"Unrealized P/L: ${current['unrealizedPL']:.2f}")
    print(f"Total P/L: ${current['totalPL']:.2f}\n")


# ============================================
# CLI - Línea de comandos
# ============================================

def main():
    """Función principal para CLI"""
    parser = argparse.ArgumentParser(
        description='Actualizar estadísticas del overlay de streaming'
    )

    parser.add_argument(
        '--win-streak',
        type=int,
        help='Racha de victorias actual'
    )

    parser.add_argument(
        '--realized',
        type=float,
        help='P/L realizado'
    )

    parser.add_argument(
        '--unrealized',
        type=float,
        help='P/L no realizado'
    )

    parser.add_argument(
        '--total-trades',
        type=int,
        help='Total de trades realizados'
    )

    parser.add_argument(
        '--win-rate',
        type=float,
        help='Porcentaje de win rate (0-100)'
    )

    parser.add_argument(
        '--increment-streak',
        action='store_true',
        help='Incrementar racha de victorias en 1'
    )

    parser.add_argument(
        '--reset-streak',
        action='store_true',
        help='Resetear racha de victorias a 0'
    )

    parser.add_argument(
        '--show',
        action='store_true',
        help='Mostrar estadísticas actuales'
    )

    parser.add_argument(
        '--example',
        action='store_true',
        help='Ejecutar ejemplos de uso'
    )

    args = parser.parse_args()

    updater = OverlayStatsUpdater()

    # Ejecutar ejemplos
    if args.example:
        example_usage()
        return

    # Mostrar stats
    if args.show:
        stats = updater.get_current_stats()
        print(json.dumps(stats, indent=2))
        return

    # Incrementar streak
    if args.increment_streak:
        new_streak = updater.increment_win_streak()
        print(f"✅ Win streak incrementado a: {new_streak}")
        return

    # Reset streak
    if args.reset_streak:
        updater.reset_win_streak()
        print("❌ Win streak reseteado a 0")
        return

    # Actualizar stats
    if any([args.win_streak, args.realized, args.unrealized,
            args.total_trades, args.win_rate]):
        stats = updater.update_stats(
            win_streak=args.win_streak,
            realized_pl=args.realized,
            unrealized_pl=args.unrealized,
            total_trades=args.total_trades,
            win_rate=args.win_rate
        )
        print("✅ Estadísticas actualizadas:")
        print(f"   Win Streak: {stats['winStreak']}")
        print(f"   Realized P/L: ${stats['realizedPL']:.2f}")
        print(f"   Unrealized P/L: ${stats['unrealizedPL']:.2f}")
        print(f"   Total P/L: ${stats['totalPL']:.2f}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()


# ============================================
# INTEGRACIÓN CON TU PROYECTO stock-analyzer
# ============================================

"""
Para integrar con tu proyecto actual:

1. Desde TradingSystem o ManualPositionTracker:

from update_overlay_stats import OverlayStatsUpdater

class TradingSystem:
    def __init__(self):
        self.overlay = OverlayStatsUpdater()

    def close_position(self, symbol):
        # ... tu código existente ...

        # Actualizar overlay
        self.overlay.update_stats(
            realized_pl=self.total_realized_pnl,
            unrealized_pl=self.total_unrealized_pnl
        )


2. Después de cada trade en Pokémon:

overlay = OverlayStatsUpdater()

# Si ganas
overlay.increment_win_streak()

# Si pierdes
overlay.reset_win_streak()


3. Actualización periódica (en un loop o timer):

import time

overlay = OverlayStatsUpdater()

while True:
    stats = overlay.update_stats(
        realized_pl=get_realized_pl(),
        unrealized_pl=get_unrealized_pl(),
        win_streak=get_current_win_streak()
    )
    time.sleep(5)  # Actualizar cada 5 segundos
"""
