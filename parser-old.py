# Converts the FileMaker Design Report XML to Nodes and adds them to the graph database

import xml.etree.ElementTree as ET
import xmltodict
import json

from models import Node, NodeType, EdgeType
import database



use_backup = False

if use_backup:
    import os, shutil
    if os.path.exists("data/graph.db"):
        os.remove("data/graph.db")
        shutil.copy("data/graph.db.bak", "data/graph.db")
        database.init_db(reset=False)
else:
    database.init_db(reset=True)






tree = ET.parse("data/Example.xml")
root = tree.getroot()



def output(some_json: dict):
    with open(f"data/test.json", "w") as f:
        f.write(json.dumps(some_json, indent=2))

def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]

def parse_BaseTableCatalog(json_dict):
    catalog = json_dict.get("BaseTableCatalog", {})
    tables  = as_list(catalog.get("BaseTable"))

    for table in tables:
        # save table node with FileMaker ID
        table_filemaker_id = table.get("@id")
        table_node = Node(table["@name"], NodeType.BASE_TABLE, table, filemaker_id=table_filemaker_id)
        table_node.save()

        # get fields safely (could be missing/None or a single dict)
        field_catalog = table.get("FieldCatalog") or {}
        fields = as_list(field_catalog.get("Field"))

        if not fields:
            print(f"[warn] Table '{table_node.name}' has no FieldCatalog/Field")
            continue

        for field in fields:
            field_filemaker_id = field.get("@id")
            field_node = Node(field["@name"], NodeType.FIELD, field, filemaker_id=field_filemaker_id)
            field_node.save()
            table_node.add_child(field_node, EdgeType.CONTAINS)


def parse_BaseDirectoryCatalog(json_dict):
    pass


def parse_RelationshipGraph(json_dict):
    graph = json_dict.get("RelationshipGraph", {})
    tables = as_list(graph.get("TableList", {}).get("Table"))

    for table in tables:

        base_id = table["@baseTableId"]

        # Find the BaseTable node by FileMaker ID (much faster than JSON extraction)
        table_node = Node.load_by_filemaker_id(str(base_id))
        if not table_node:
            print(f"[warn] BaseTable id {base_id} not found for rel table {table.get('@name')}")
            continue

        # Create a node for the relationship-graph table instance with FileMaker ID
        rel_table_filemaker_id = table.get("@id")
        rel_table_node = Node(table["@name"], NodeType.REL_TABLE, table, filemaker_id=rel_table_filemaker_id)
        rel_table_node.save()

        # Make BaseTable -> RelTable a parent relationship
        table_node.add_child(rel_table_node, EdgeType.PARENT)

    relationships = as_list(graph.get("RelationshipList", {}).get("Relationship"))

    for rel in relationships:
        left_name  = rel["LeftTable"]["@name"]
        right_name = rel["RightTable"]["@name"]

        # Find left/right REL_TABLE nodes by name
        left_table_nodes = Node.find(
            where="type = ? AND name = ?",
            params=(NodeType.REL_TABLE.value, left_name),
        )
        right_table_nodes = Node.find(
            where="type = ? AND name = ?",
            params=(NodeType.REL_TABLE.value, right_name),
        )
        
        if not left_table_nodes:
            print(f"[warn] Left REL_TABLE '{left_name}' not found for relationship")
            continue
        if not right_table_nodes:
            print(f"[warn] Right REL_TABLE '{right_name}' not found for relationship")
            continue

        left_table_node = left_table_nodes[0]
        right_table_node = right_table_nodes[0]

        # Create ONE relationship node for this relationship
        rel_filemaker_id = rel.get("@id")
        rel_node = Node(f"{left_name}->{right_name}", NodeType.RELATIONSHIP, rel, filemaker_id=rel_filemaker_id)
        rel_node.save()

        # Connect relationship to both tables
        left_table_node.add_child(rel_node, EdgeType.PARENT)
        rel_node.add_child(right_table_node, EdgeType.PARENT)

        # Process each join predicate to connect the relationship to the fields
        join_predicates = rel["JoinPredicateList"]["JoinPredicate"]
        if type(join_predicates) != list: 
            join_predicates = [join_predicates]

        for predicate in join_predicates:
            left_field_id = predicate["LeftField"]["Field"]["@id"]
            right_field_id = predicate["RightField"]["Field"]["@id"]

            # Find the field nodes by their FileMaker IDs
            left_field_node = Node.load_by_filemaker_id(str(left_field_id))
            right_field_node = Node.load_by_filemaker_id(str(right_field_id))
            
            # Connect relationship to the fields used in this predicate
            if left_field_node:
                rel_node.add_child(left_field_node, EdgeType.USED_BY)
            else:
                print(f"[warn] Left field ID {left_field_id} not found for relationship")
                
            if right_field_node:
                rel_node.add_child(right_field_node, EdgeType.USED_BY)
            else:
                print(f"[warn] Right field ID {right_field_id} not found for relationship")


def parse_LayoutObjects(object_list, layout_node: Node):
    for obj in object_list:
        # Create a node for the object with FileMaker ID
        output(obj)
        exit()
        obj_filemaker_id = obj.get("@id")
        obj_node = Node(obj["@name"], NodeType.LAYOUT_OBJECT, obj, filemaker_id=obj_filemaker_id)
        obj_node.save()
        # Relate the object to the layout
        layout_node.add_child(obj_node, EdgeType.PARENT)

        # Check if this object has a field reference
        field_obj = obj.get("FieldObj")
        if field_obj and field_obj.get("Name"):
            # Removes the table name to get the field name
            field_name = field_obj.get("Name").split("::", 1)[1]

            # Try to find the field by name (could be improved if we had field FileMaker IDs in the field reference)
            field_nodes = Node.find(
                where="type = ? AND name = ?",
                params=(NodeType.FIELD.value, field_name),
            )
            
            if field_nodes:
                # Create a relationship between the layout object and the field
                obj_node.add_child(field_nodes[0], EdgeType.USED_BY)



def parse_LayoutCatalog(json_dict):
    catalog = json_dict.get("LayoutCatalog", {})
    layouts = as_list(catalog.get("Layout"))

    for layout in layouts:
        # Create layout node with FileMaker ID
        layout_filemaker_id = layout.get("@id")
        layout_node = Node(layout["@name"], NodeType.LAYOUT, layout, filemaker_id=layout_filemaker_id)
        layout_node.save()

        # Find the relationship graph table by FileMaker ID (much faster)
        table_id = layout["Table"]["@id"]
        table_node = Node.load_by_filemaker_id(str(table_id))
        if not table_node:
            print(f"[warn] Layout table id {table_id} not found for layout {layout.get('@name')}")
            continue

        # Relate the layout to the table
        table_node.add_child(layout_node, EdgeType.USED_BY)

        # "Object" is a list but if theres only 1 thing in the list then theres no wrapping square brackets
        # So this code turns it into a list if not already
        object_list = layout.get("Object", [])
        object_list = object_list if isinstance(object_list, list) else [object_list]
        parse_LayoutObjects(object_list, layout_node)



        if layout["@name"] not in ["Startup Screen", "Contactss | Addresses | 5160"]:
            output(layout)
            break
        else:
            print(f"[info] Skipping layout {layout['@name']} as it is not a test case.")

parser_functions = {
    "BaseTableCatalog": parse_BaseTableCatalog,
    "BaseDirectoryCatalog": parse_BaseDirectoryCatalog,
    "RelationshipGraph": parse_RelationshipGraph,
    "LayoutCatalog": parse_LayoutCatalog
}


for section in root[0]:

    if section.tag in parser_functions:
        if use_backup and section.tag != "LayoutCatalog":
            # When using backup, skip sections that are already in the db (except LayoutCatalog for testing)
            print(f"Skipping {section.tag} since its already in the db")
        else:
            # Process all sections when not using backup, or LayoutCatalog when using backup
            print("Processing section:", section.tag)
            # Convert the section element to a dictionary using xmltodict
            section_dict = xmltodict.parse(ET.tostring(section, encoding='unicode'))
            parser_functions[section.tag](section_dict)
    else:
        print(f"No parser function for {section.tag}!")
        break
