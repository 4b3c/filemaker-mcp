import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import json
import os

DB_PATH = "data/graph.db"

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                type    TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS edges (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                type     TEXT NOT NULL,
                from_id  INTEGER NOT NULL,
                to_id    INTEGER NOT NULL,
                FOREIGN KEY(from_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY(to_id)   REFERENCES nodes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
            CREATE INDEX IF NOT EXISTS idx_edges_to   ON edges(to_id);
            """
        )

# --- Node CRUD ---

def node_insert(name: str, type_value: str, details: Dict[str, Any]) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO nodes (name, type, details) VALUES (?, ?, ?)",
            (name, type_value, json.dumps(details)),
        )
        return cur.lastrowid

def node_update(node_id: int, name: str, type_value: str, details: Dict[str, Any]) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE nodes SET name = ?, type = ?, details = ? WHERE id = ?",
            (name, type_value, json.dumps(details), node_id),
        )
        return cur.rowcount > 0

def node_get_by_id(node_id: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()

def node_find(where: Optional[str] = None, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    sql = "SELECT * FROM nodes"
    if where:
        sql += f" WHERE {where}"
    with _connect() as conn:
        return conn.execute(sql, params).fetchall()

def node_delete(node_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        return cur.rowcount > 0

# --- Edge CRUD ---

def edge_insert(type_value: str, from_id: int, to_id: int) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO edges (type, from_id, to_id) VALUES (?, ?, ?)",
            (type_value, from_id, to_id),
        )
        return cur.lastrowid

def edge_update(edge_id: int, type_value: str, from_id: int, to_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE edges SET type = ?, from_id = ?, to_id = ? WHERE id = ?",
            (type_value, from_id, to_id, edge_id),
        )
        return cur.rowcount > 0

def edge_get_by_id(edge_id: int) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM edges WHERE id = ?", (edge_id,)).fetchone()

def edge_find(where: Optional[str] = None, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    sql = "SELECT * FROM edges"
    if where:
        sql += f" WHERE {where}"
    with _connect() as conn:
        return conn.execute(sql, params).fetchall()

def edge_delete(edge_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))
        return cur.rowcount > 0

# --- Neighbor queries ---

def children_of(parent_id: int) -> List[sqlite3.Row]:
    sql = (
        "SELECT n.*, e.type AS edge_type, e.id AS edge_id "
        "FROM edges e JOIN nodes n ON n.id = e.to_id "
        "WHERE e.from_id = ? ORDER BY n.id"
    )
    with _connect() as conn:
        return conn.execute(sql, (parent_id,)).fetchall()

def parents_of(child_id: int) -> List[sqlite3.Row]:
    sql = (
        "SELECT n.*, e.type AS edge_type, e.id AS edge_id "
        "FROM edges e JOIN nodes n ON n.id = e.from_id "
        "WHERE e.to_id = ? ORDER BY n.id"
    )
    with _connect() as conn:
        return conn.execute(sql, (child_id,)).fetchall()

# --- Utility ---

def reset_all() -> None:
    with _connect() as conn:
        conn.executescript("""
            DROP TABLE IF EXISTS edges;
            DROP TABLE IF EXISTS nodes;
        """)
        init_db()
