# Converts the FileMaker Design Report XML to Nodes and adds them to the graph database

import xml.etree.ElementTree as ET
import xmltodict
import json

import database as db


tree = ET.parse("data/Example.xml")
root = tree.getroot()



def output(some_json):
    with open(f"data/test.json", "w") as f:
        f.write(json.dumps(some_json, indent=2))


def parse_BaseTableCatalog(json_dict):
    tables = json_dict["BaseTableCatalog"]["BaseTable"]
    for table in tables:
        table_json = {type}
        db.insert(db.Node, )

    output(tables[0])


parser_functions = {
    "BaseTableCatalog": parse_BaseTableCatalog
}


for section in root[0]:
    # Convert the section element to a dictionary using xmltodict
    section_dict = xmltodict.parse(ET.tostring(section, encoding='unicode'))
    parser_functions[section.tag](section_dict)
    
    break
