from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import database

class NodeType(str, Enum):
    UNKNOWN      = "Unknown"
    ACCOUNT      = "Account"
    BASE_TABLE   = "BaseTable"
    FIELD        = "Field"

class EdgeType(str, Enum):
    UNKNOWN      = "Unknown"
    PARENT       = "Parent"
    IS           = "Is"
    CONTAINS     = "Contains"

class Node:
    def __init__(self, name: str, type: NodeType = NodeType.UNKNOWN,
                 details: Optional[Dict[str, Any]] = None, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.type = type
        self.details = details or {}

    def save(self) -> int:
        if self.id is None:
            self.id = database.node_insert(self.name, self.type.value, self.details)
        else:
            database.node_update(self.id, self.name, self.type.value, self.details)
        return self.id

    def add_child(self, child: "Node", rel_type: EdgeType = EdgeType.UNKNOWN) -> int:
        if self.id is None:
            self.save()
        if child.id is None:
            child.save()
        return database.edge_insert(rel_type.value, self.id, child.id)

    def get_children(self) -> List[Tuple["Node", EdgeType, int]]:
        rows = database.children_of(self.id)
        return [(
            Node(
                id=r["id"],
                name=r["name"],
                type=NodeType(r["type"]),
                details=json.loads(r["details"]) if r["details"] else {},
            ),
            EdgeType(r["edge_type"]),
            r["edge_id"],
        ) for r in rows]

    def get_parents(self) -> List[Tuple["Node", EdgeType, int]]:
        rows = database.parents_of(self.id)
        return [(
            Node(
                id=r["id"],
                name=r["name"],
                type=NodeType(r["type"]),
                details=json.loads(r["details"]) if r["details"] else {},
            ),
            EdgeType(r["edge_type"]),
            r["edge_id"],
        ) for r in rows]

    @classmethod
    def load(cls, node_id: int) -> Optional["Node"]:
        row = database.node_get_by_id(node_id)
        if not row:
            return None
        return cls(
            id=row["id"],
            name=row["name"],
            type=NodeType(row["type"]),
            details=json.loads(row["details"]) if row["details"] else {},
        )

    @classmethod
    def find(cls, where: Optional[str] = None, params: Tuple[Any, ...] = (),
        ) -> List["Node"]:
        rows = database.node_find(where, params)
        return [
            cls(
                id=r["id"],
                name=r["name"],
                type=NodeType(r["type"]),
                details=json.loads(r["details"]) if r["details"] else {},
            )
            for r in rows
        ]

class Edge:
    def __init__(self, type: EdgeType = EdgeType.UNKNOWN, from_id: int = 0,
                 to_id: int = 0, id: Optional[int] = None):
        self.id = id
        self.type = type
        self.from_id = from_id
        self.to_id = to_id

    def save(self) -> int:
        if self.id is None:
            self.id = database.edge_insert(self.type.value, self.from_id, self.to_id)
        else:
            database.edge_update(self.id, self.type.value, self.from_id, self.to_id)
        return self.id

    @classmethod
    def load(cls, edge_id: int) -> Optional["Edge"]:
        row = database.edge_get_by_id(edge_id)
        if not row:
            return None
        return cls(
            id=row["id"],
            type=EdgeType(row["type"]),
            from_id=row["from_id"],
            to_id=row["to_id"],
        )
