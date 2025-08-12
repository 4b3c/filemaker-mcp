import database
from collections import Counter

database.init_db()

nodes = database.node_find()
print(f"Found {len(nodes)} nodes!")

# Count by type
type_counts = Counter(row["type"] for row in nodes)
print("\nNode type counts:")
for t, count in type_counts.items():
    print(f"  {t}: {count}")
