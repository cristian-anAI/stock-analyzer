# crypto_dashboard.py
"""
CryptoDashboard: Displays crypto positions, P&L, and volatility alerts separately from stocks.
- 24/7 monitoring support
- Volatility alerts for crypto
"""
from position_manager import PositionManager

class CryptoDashboard:
    def __init__(self, position_manager=None):
        self.position_manager = position_manager or PositionManager()

    def show(self):
        crypto_positions = [p for p in self.position_manager.positions.values() if getattr(p, 'symbol', '').endswith('-USD')]
        print("\n================ CRYPTO PORTFOLIO DASHBOARD ================")
        if not crypto_positions:
            print("No crypto positions open.")
            return
        total_pnl = sum(p.unrealized_pnl for p in crypto_positions)
        print(f"Crypto positions: {len(crypto_positions)}")
        print(f"Total P&L: ${total_pnl:.2f}")
        for pos in crypto_positions:
            print(f"{pos.symbol}: {pos.quantity} @ ${pos.entry_price:.2f} | Now: ${pos.current_price:.2f} | P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_percent:+.1f}%)")
            # Volatility alert example
            if abs(pos.unrealized_pnl_percent) > 15:
                print(f"  [ALERT] High volatility: {pos.unrealized_pnl_percent:+.1f}%")
        print("============================================================\n")
