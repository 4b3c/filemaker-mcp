from enum import Enum
from typing import Optional
from sqlmodel import Relationship, SQLModel, Field, create_engine, Session, select
from sqlalchemy import Column, Enum as SAEnum, UniqueConstraint, JSON
from sqlalchemy.orm import joinedload

class ObjectType(str, Enum):
    UNKNOWN = "Unknown"
    ACCOUNT = "Account"
    BASE_TABLE = "BaseTable"
    FIELDS  = "Fields"


class Node(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: ObjectType = Field(
        default=ObjectType.UNKNOWN,
        sa_column=Column(SAEnum(ObjectType, native_enum=False), nullable=False)
    )
    name: str
    details: dict = Field(sa_column=Column(JSON, nullable=False))

    edges_out: list["Edge"] = Relationship(
        back_populates="from_node",
        sa_relationship_kwargs={"foreign_keys": "[Edge.from_node_id]"}
    )
    edges_in: list["Edge"] = Relationship(
        back_populates="to_node",
        sa_relationship_kwargs={"foreign_keys": "[Edge.to_node_id]"}
    )


class Edge(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("from_node_id", "to_node_id"),)
    id: int | None = Field(default=None, primary_key=True)
    from_node_id: int = Field(foreign_key="node.id")
    to_node_id: int = Field(foreign_key="node.id")
    relationship: str = Field(default="related")

    from_node: Optional[Node] = Relationship(
        back_populates="edges_out",
        sa_relationship_kwargs={"foreign_keys": "[Edge.from_node_id]"}
    )
    to_node: Optional[Node] = Relationship(
        back_populates="edges_in",
        sa_relationship_kwargs={"foreign_keys": "[Edge.to_node_id]"}
    )


engine = create_engine("sqlite:///graph.db")
SQLModel.metadata.create_all(engine)

# ---------- generic CRUD ops ----------
def create(obj_cls, data: dict):
    with Session(engine) as s:
        obj = obj_cls(**data)
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj

def read(obj_cls, obj_id: int):
    with Session(engine) as s:
        return s.get(obj_cls, obj_id)

def update(obj_cls, obj_id: int, data: dict):
    with Session(engine) as s:
        obj = s.get(obj_cls, obj_id)
        for k, v in data.items():
            setattr(obj, k, v)
        s.commit()
        s.refresh(obj)
        return obj

def delete(obj_cls, obj_id: int):
    with Session(engine) as s:
        obj = s.get(obj_cls, obj_id)
        if obj:
            s.delete(obj)
            s.commit()
        return bool(obj)

# ---------- helpers ----------
def get_related_nodes(node_id: int):
    with Session(engine) as session:
        # Load outgoing edges with to_node preloaded
        edges = session.exec(
            select(Edge)
            .where(Edge.from_node_id == node_id)
            .options(joinedload(Edge.to_node))
        ).all()

        # Format output
        return [
            {
                "to": edge.to_node.name if edge.to_node else None,
                "type": edge.to_node.type if edge.to_node else None,
                "relationship": edge.relationship
            }
            for edge in edges
        ]







node_json1 = {"type": "ACCOUNT", "name": "Main", "details": {"owner": "John"}}
node_json2 = {"type": "ACCOUNT", "name": "Alt", "details": {"owner": "John"}}
n1 = create(Node, node_json1)
n2 = create(Node, node_json2)
edge_json1 = {"from_node_id": n1.id, "to_node_id": n2.id, "relationship": "same user"}
e1 = create(Edge, edge_json1)

related = get_related_nodes(n1.id)
print(related)