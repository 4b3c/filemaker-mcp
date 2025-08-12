# Converts the FileMaker Design Report XML to Nodes and adds them to the graph database

import xml.etree.ElementTree as ET
import xmltodict
import json

from models import Node, NodeType, EdgeType
import database

database.init_db(reset=True)

tree = ET.parse("data/Example.xml")
root = tree.getroot()



def output(some_json: dict):
    with open(f"data/test.json", "w") as f:
        f.write(json.dumps(some_json, indent=2))

def remove_keys(d: dict, *keys) -> dict:
    return {k: v for k, v in d.items() if k not in keys}

def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def parse_BaseTableCatalog(json_dict):
    catalog = json_dict.get("BaseTableCatalog", {})
    tables  = as_list(catalog.get("BaseTable"))

    for table in tables:
        # save table node (omit FieldCatalog from details)
        table_node = Node(table["@name"], NodeType.BASE_TABLE, remove_keys(table, "FieldCatalog"))
        table_node.save()

        # get fields safely (could be missing/None or a single dict)
        field_catalog = table.get("FieldCatalog") or {}
        fields = as_list(field_catalog.get("Field"))

        if not fields:
            print(f"[warn] Table '{table_node.name}' has no FieldCatalog/Field")
            continue

        for field in fields:
            field_node = Node(field["@name"], NodeType.FIELD, field)
            field_node.save()
            table_node.add_child(field_node, EdgeType.CONTAINS)


def parse_BaseDirectoryCatalog(json_dict):
    pass


def parse_RelationshipGraph(json_dict):
    graph = json_dict.get("RelationshipGraph", {})
    tables = as_list(graph.get("TableList", {}).get("Table"))

    for table in tables:

        base_id = table["@baseTableId"]

        # Find the BaseTable node whose details["@id"] == base_id
        # (details stored as JSON text; we use SQLite JSON1)
        rows = database.node_find(
            where='type = ? AND json_extract(details, \'$."@id"\') = ?',
            params=(NodeType.BASE_TABLE.value, str(base_id)),
        )
        if not rows:
            print(f"[warn] BaseTable id {base_id} not found for rel table {table.get('@name')}")
            continue

        table_node_id = rows[0]["id"]
        table_node = Node.load(table_node_id)

        # Create a node for the relationship-graph table instance
        rel_table_node = Node(table["@name"], NodeType.REL_TABLE, table)
        rel_table_node.save()

        # Make BaseTable -> RelTable a parent relationship
        table_node.add_child(rel_table_node, EdgeType.PARENT)

    relationships = as_list(graph.get("RelationshipList", {}).get("Relationship"))

    for rel in relationships:
        rel_id = rel["@id"]
        left_name  = rel["LeftTable"]["@name"]
        right_name = rel["RightTable"]["@name"]

        # Find left/right REL_TABLE nodes by name
        left_row = database.node_find(
            where="type = ? AND name = ?",
            params=(NodeType.REL_TABLE.value, left_name),
        )[0]
        right_row = database.node_find(
            where="type = ? AND name = ?",
            params=(NodeType.REL_TABLE.value, right_name),
        )[0]

        left_node  = Node.load(left_row["id"])
        right_node = Node.load(right_row["id"])
        rel_node = Node(f"{left_name}->{right_name}", NodeType.RELATIONSHIP, rel)
        rel_node.save()

        # Wire it: Left → Relationship (parent of), Relationship → Right (parent of)
        left_node.add_child(rel_node, EdgeType.PARENT)
        rel_node.add_child(right_node, EdgeType.PARENT)


parser_functions = {
    "BaseTableCatalog": parse_BaseTableCatalog,
    "BaseDirectoryCatalog": parse_BaseDirectoryCatalog,
    "RelationshipGraph": parse_RelationshipGraph
}


for section in root[0]:
    # Convert the section element to a dictionary using xmltodict
    section_dict = xmltodict.parse(ET.tostring(section, encoding='unicode'))
    print("Processing section:", section.tag)

    if section.tag in parser_functions:
        parser_functions[section.tag](section_dict)
    else:
        print(f"No parser function for {section.tag}!")
        break
