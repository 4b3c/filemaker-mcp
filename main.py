from models import Node, NodeType, EdgeType
import database

if __name__ == "__main__":
    # 1) Initialize DB (creates graph.db and tables if missing)
    database.init_db()

    # 2) Create a couple nodes
    parent = Node(name="Accounts", type=NodeType.ACCOUNT, details={"owner": "sys"})
    child  = Node(name="Users", type=NodeType.BASE_TABLE, details={"rows": 42})

    # 3) Save them (insert on first call; update on subsequent calls)
    parent.save()
    child.save()

    # 4) Relate them: parent -> child with a relationship type
    parent.addChild(child, EdgeType.CONTAINS)

    # 5) Query children from the parent
    children = parent.getChildren()
    print("Children of", parent.name)
    for n, rel, edge_id in children:
        print(f"  - {n.id}:{n.name} [{rel.value}] via edge {edge_id}")

    # 6) Query parents from the child
    parents = child.getParents()
    print("Parents of", child.name)
    for n, rel, edge_id in parents:
        print(f"  - {n.id}:{n.name} [{rel.value}] via edge {edge_id}")

    # 7) Show a fresh load from DB to demonstrate persistence
    same_parent = Node.load(parent.id)
    same_childs = same_parent.getChildren() if same_parent else []
    print("Reloaded parent -> children:")
    for n, rel, edge_id in same_childs:
        print(f"  - {n.id}:{n.name} [{rel.value}] via edge {edge_id}")
