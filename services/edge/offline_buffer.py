"""
Offline Buffer - Phase 2 Member 1 deliverable

Stores telemetry locally when network drops.
Replays in order when connection restored.
Thread-safe SQLite backend.
"""

import sqlite3
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class OfflineBuffer:
    """SQLite-based local buffer for telemetry when offline"""

    def __init__(self, db_path: str = "/tmp/telemetry_buffer.db"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Telemetry buffer table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    operator_id TEXT,
                    task_id TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0
                )
            """)

            # Alerts buffer table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT NOT NULL,
                    operator_id TEXT,
                    site_id TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    synced BOOLEAN DEFAULT 0
                )
            """)

            # Index for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp
                ON telemetry_buffer(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_telemetry_machine
                ON telemetry_buffer(machine_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
                ON alerts_buffer(timestamp)
            """)

            conn.commit()
            conn.close()

            logger.info(f"Offline buffer initialized at {self.db_path}")

    def store_telemetry(self, telemetry: Dict) -> bool:
        """Store telemetry row locally"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO telemetry_buffer
                    (timestamp, site_id, machine_id, operator_id, task_id, payload)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    telemetry.get('timestamp'),
                    telemetry.get('site_id'),
                    telemetry.get('machine_id'),
                    telemetry.get('operator_id'),
                    telemetry.get('task_id'),
                    json.dumps(telemetry)
                ))

                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"Error storing telemetry: {e}")
            return False

    def store_alert(self, alert: Dict) -> bool:
        """Store alert locally"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR IGNORE INTO alerts_buffer
                    (alert_id, timestamp, machine_id, operator_id, site_id,
                     rule, severity, message, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.get('alert_id'),
                    alert.get('timestamp'),
                    alert.get('machine_id'),
                    alert.get('operator_id'),
                    alert.get('site_id'),
                    alert.get('rule'),
                    alert.get('severity'),
                    alert.get('message'),
                    json.dumps(alert)
                ))

                conn.commit()
                conn.close()
                return True
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
            return False

    def get_unsynced_telemetry(self, limit: int = 1000) -> List[Dict]:
        """Get telemetry rows not yet synced to cloud"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM telemetry_buffer
                    WHERE synced = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (limit,))

                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()

                return rows
        except Exception as e:
            logger.error(f"Error reading telemetry buffer: {e}")
            return []

    def get_unsynced_alerts(self, limit: int = 100) -> List[Dict]:
        """Get alerts not yet synced to cloud"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM alerts_buffer
                    WHERE synced = 0
                    ORDER BY timestamp ASC
                    LIMIT ?
                """, (limit,))

                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()

                return rows
        except Exception as e:
            logger.error(f"Error reading alerts buffer: {e}")
            return []

    def mark_telemetry_synced(self, row_ids: List[int]) -> bool:
        """Mark telemetry rows as synced"""
        if not row_ids:
            return True

        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                placeholders = ','.join('?' * len(row_ids))
                cursor.execute(f"""
                    UPDATE telemetry_buffer SET synced = 1 WHERE id IN ({placeholders})
                """, row_ids)

                conn.commit()
                conn.close()
                logger.info(f"Marked {len(row_ids)} telemetry rows as synced")
                return True
        except Exception as e:
            logger.error(f"Error marking telemetry synced: {e}")
            return False

    def mark_alerts_synced(self, alert_ids: List[str]) -> bool:
        """Mark alerts as synced"""
        if not alert_ids:
            return True

        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                for alert_id in alert_ids:
                    cursor.execute("""
                        UPDATE alerts_buffer SET synced = 1 WHERE alert_id = ?
                    """, (alert_id,))

                conn.commit()
                conn.close()
                logger.info(f"Marked {len(alert_ids)} alerts as synced")
                return True
        except Exception as e:
            logger.error(f"Error marking alerts synced: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get buffer statistics"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM telemetry_buffer WHERE synced = 0")
                unsynced_telemetry = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM telemetry_buffer")
                total_telemetry = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM alerts_buffer WHERE synced = 0")
                unsynced_alerts = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM alerts_buffer")
                total_alerts = cursor.fetchone()[0]

                # Get database size
                db_size = Path(self.db_path).stat().st_size / 1024  # KB

                conn.close()

                return {
                    "telemetry": {
                        "total": total_telemetry,
                        "unsynced": unsynced_telemetry
                    },
                    "alerts": {
                        "total": total_alerts,
                        "unsynced": unsynced_alerts
                    },
                    "database_size_kb": db_size
                }
        except Exception as e:
            logger.error(f"Error getting buffer stats: {e}")
            return {}

    def clear_synced(self, days_old: int = 7) -> bool:
        """Clear synced data older than N days"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Calculate cutoff time
                cutoff = datetime.utcnow().isoformat()

                cursor.execute("""
                    DELETE FROM telemetry_buffer
                    WHERE synced = 1 AND created_at < datetime('now', '-' || ? || ' days')
                """, (days_old,))

                cursor.execute("""
                    DELETE FROM alerts_buffer
                    WHERE synced = 1 AND created_at < datetime('now', '-' || ? || ' days')
                """, (days_old,))

                deleted = cursor.rowcount
                conn.commit()
                conn.close()

                logger.info(f"Cleared {deleted} old synced records")
                return True
        except Exception as e:
            logger.error(f"Error clearing buffer: {e}")
            return False


if __name__ == "__main__":
    # Test the offline buffer
    logging.basicConfig(level=logging.INFO)

    buffer = OfflineBuffer(db_path="/tmp/test_buffer.db")

    # Store some test data
    test_telemetry = {
        "timestamp": "2025-05-01T08:00:00Z",
        "site_id": "S01",
        "machine_id": "BH001",
        "operator_id": "OP1011",
        "task_id": "T00028",
        "fuel_level_pct": 85.0
    }

    buffer.store_telemetry(test_telemetry)

    # Get stats
    stats = buffer.get_stats()
    print(f"Buffer stats: {stats}")
