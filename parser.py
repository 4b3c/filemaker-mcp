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
        table_node = Node(
            table.get("@name", "Unnamed"),
            NodeType.BASE_TABLE,
            remove_keys(table, "FieldCatalog"),
        )
        table_node.save()

        # get fields safely (could be missing/None or a single dict)
        field_catalog = table.get("FieldCatalog") or {}
        fields = as_list(field_catalog.get("Field"))

        if not fields:
            print(f"[warn] Table '{table_node.name}' has no FieldCatalog/Field")

        for field in fields:
            field_node = Node(field.get("@name", "UnnamedField"),
                              NodeType.FIELD,
                              field)
            field_node.save()
            table_node.add_child(field_node, EdgeType.CONTAINS)

parser_functions = {
    "BaseTableCatalog": parse_BaseTableCatalog
}


for section in root[0]:
    # Convert the section element to a dictionary using xmltodict
    section_dict = xmltodict.parse(ET.tostring(section, encoding='unicode'))
    parser_functions[section.tag](section_dict)
    
    break
