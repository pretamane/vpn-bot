#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import subprocess
import sys
import os
import re

def find_source_files(query):
    """
    Searches for the query string in the current directory using grep.
    Returns a list of matching file paths and line numbers.
    """
    if not query or query == "NO_ID":
        return []

    # Clean up the ID (remove package name if present)
    clean_query = query.split('/')[-1]
    
    try:
        # Search in layout files first (high priority)
        layout_cmd = ["grep", "-rn", clean_query, "NekoBoxForAndroid/app/src/main/res/layout"]
        layout_results = subprocess.run(layout_cmd, capture_output=True, text=True).stdout.strip().split('\n')
        
        # Search in code files (secondary priority)
        code_cmd = ["grep", "-rn", clean_query, "NekoBoxForAndroid/app/src/main/java"]
        code_results = subprocess.run(code_cmd, capture_output=True, text=True).stdout.strip().split('\n')
        
        results = []
        for line in layout_results + code_results:
            if line:
                parts = line.split(':', 2)
                if len(parts) >= 2:
                    results.append(f"{parts[0]}:{parts[1]}")
        return results[:3] # Return top 3 matches to avoid clutter
    except Exception:
        return []

def print_node(node, depth=0):
    """
    Recursively prints the node tree.
    """
    resource_id = node.attrib.get('resource-id', '')
    text = node.attrib.get('text', '')
    class_name = node.attrib.get('class', '').split('.')[-1]
    bounds = node.attrib.get('bounds', '')
    
    # Only print interesting nodes (has ID, text, or is a button/input)
    is_interesting = resource_id or text or "Button" in class_name or "EditText" in class_name
    
    if is_interesting:
        indent = "  " * depth
        display_id = resource_id.split('/')[-1] if resource_id else "NO_ID"
        display_text = f'"{text}"' if text else ""
        
        print(f"{indent}['{class_name}'] {display_text} ({display_id})")
        print(f"{indent}  ├── Bounds: {bounds}")
        
        if display_id != "NO_ID":
            sources = find_source_files(display_id)
            if sources:
                for source in sources:
                    if "layout" in source:
                        print(f"{indent}  ├── Layout: {source}")
                    else:
                        print(f"{indent}  └── Code:   {source}")
            else:
                 print(f"{indent}  └── Code:   (Not found)")
        print("")

    for child in node:
        print_node(child, depth + 1)

def main():
    if len(sys.argv) < 2:
        print("Usage: ./inspect_ui.py <path_to_window_dump.xml>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        print(f"--- UI Inspection: {file_path} ---")
        print_node(root)
    except ET.ParseError:
        print("Error: Failed to parse XML.")

if __name__ == "__main__":
    main()
