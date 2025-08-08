import sqlite3
import os
import csv
from datetime import datetime
from typing import List, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str = "trading.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            entry_date TEXT,
            entry_price REAL,
            quantity INTEGER,
            stop_loss REAL,
            take_profit REAL,
            current_price REAL,
            unrealized_pnl REAL,
            unrealized_pnl_percent REAL,
            days_held INTEGER,
            trailing_stop REAL,
            partial_sold INTEGER,
            notes TEXT,
            position_type TEXT DEFAULT 'AUTO'
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS trades_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            entry_date TEXT,
            exit_date TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity INTEGER,
            pnl REAL,
            pnl_percent REAL,
            reason TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            total_pnl REAL,
            total_positions INTEGER
        )''')
        self.conn.commit()

    def save_position(self, pos: Dict[str, Any]):
        c = self.conn.cursor()
        c.execute('''INSERT INTO positions (symbol, entry_date, entry_price, quantity, stop_loss, take_profit, current_price, unrealized_pnl, unrealized_pnl_percent, days_held, trailing_stop, partial_sold, notes, position_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (pos['symbol'], pos['entry_date'], pos['entry_price'], pos['quantity'], pos['stop_loss'], pos['take_profit'], pos.get('current_price', 0), pos.get('unrealized_pnl', 0), pos.get('unrealized_pnl_percent', 0), pos.get('days_held', 0), pos.get('trailing_stop', 0), int(pos.get('partial_sold', False)), pos.get('notes', ''), pos.get('position_type', 'AUTO')))
        self.conn.commit()

    def update_position(self, pos: Dict[str, Any]):
        c = self.conn.cursor()
        c.execute('''UPDATE positions SET current_price=?, unrealized_pnl=?, unrealized_pnl_percent=?, days_held=?, trailing_stop=?, partial_sold=?, notes=?, position_type=? WHERE symbol=?''',
            (pos.get('current_price', 0), pos.get('unrealized_pnl', 0), pos.get('unrealized_pnl_percent', 0), pos.get('days_held', 0), pos.get('trailing_stop', 0), int(pos.get('partial_sold', False)), pos.get('notes', ''), pos.get('position_type', 'AUTO'), pos['symbol']))
        self.conn.commit()

    def delete_position(self, symbol: str):
        c = self.conn.cursor()
        c.execute('DELETE FROM positions WHERE symbol=?', (symbol,))
        self.conn.commit()

    def save_trade_history(self, trade: Dict[str, Any]):
        c = self.conn.cursor()
        c.execute('''INSERT INTO trades_history (symbol, entry_date, exit_date, entry_price, exit_price, quantity, pnl, pnl_percent, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (trade['symbol'], trade['entry_date'], trade['exit_date'], trade['entry_price'], trade['exit_price'], trade['quantity'], trade['pnl'], trade['pnl_percent'], trade.get('reason', '')))
        self.conn.commit()

    def save_daily_snapshot(self, date: str, total_pnl: float, total_positions: int):
        c = self.conn.cursor()
        c.execute('''INSERT INTO daily_snapshots (date, total_pnl, total_positions) VALUES (?, ?, ?)''', (date, total_pnl, total_positions))
        self.conn.commit()

    def load_positions(self) -> List[Dict[str, Any]]:
        c = self.conn.cursor()
        c.execute('SELECT * FROM positions')
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        return [dict(zip(columns, row)) for row in rows]

    def export_trades_history_csv(self, filename: str = None):
        if not filename:
            filename = f"trades_history_{datetime.now().strftime('%Y%m%d')}.csv"
        c = self.conn.cursor()
        c.execute('SELECT * FROM trades_history')
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        return filename

    def daily_backup(self, backup_dir: str = "backups"):
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        backup_file = os.path.join(backup_dir, f"trading_{datetime.now().strftime('%Y%m%d')}.db")
        self.conn.commit()
        with open(self.db_path, 'rb') as src, open(backup_file, 'wb') as dst:
            dst.write(src.read())
        return backup_file

    def integrity_check(self):
        c = self.conn.cursor()
        c.execute('PRAGMA integrity_check')
        result = c.fetchone()
        return result[0] == 'ok'

    def migrate(self, migration_sql: str):
        c = self.conn.cursor()
        c.executescript(migration_sql)
        self.conn.commit()

    def close(self):
        self.conn.close()
