import json
import tkinter.ttk as ttk
from typing import Any, Optional, List

def format_table_value(value: Any, max_length: int = 180) -> str:
    if isinstance(value, (dict, list, tuple)):
        display_value = json.dumps(value, ensure_ascii=False, default=str)
    else:
        display_value = str(value)

    display_value = display_value.replace("\n", " ").replace("\r", " ")
    if len(display_value) > max_length:
        display_value = display_value[: max_length - 3] + "..."
    return display_value

def flatten_metadata_rows(data: Any, category: str = "", rows: Optional[list] = None) -> list:
    if rows is None: rows = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key).replace("_", " ")
            if isinstance(value, dict):
                nested_category = f"{category} / {key_text}" if category else key_text
                flatten_metadata_rows(value, nested_category, rows)
            elif isinstance(value, (list, tuple)) and value and all(isinstance(item, dict) for item in value):
                for index, item in enumerate(value):
                    nested_category = f"{category} / {key_text}[{index}]" if category else f"{key_text}[{index}]"
                    flatten_metadata_rows(item, nested_category, rows)
            else:
                rows.append((category, key_text, format_table_value(value)))
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            if isinstance(item, dict):
                nested_category = f"{category}[{index}]" if category else f"[{index}]"
                flatten_metadata_rows(item, nested_category, rows)
            elif isinstance(item, (list, tuple)):
                nested_category = f"{category}[{index}]" if category else f"[{index}]"
                flatten_metadata_rows(item, nested_category, rows)
            else:
                rows.append((category, f"[{index}]", format_table_value(item)))
    else:
        rows.append((category, "", format_table_value(data)))
    return rows

def populate_metadata_table(tree: ttk.Treeview, rows: list, include_category: bool, x_path: str = "", y_path: str = "") -> None:
    for item in tree.get_children():
        tree.delete(item)
    last_category = None
    for row in rows:
        if include_category:
            category, key, value = row
            
            tag_path = f"{category.strip()} / {key.strip()}" if category and key else (category.strip() or key.strip())
            use_as = ""
            if tag_path and tag_path == x_path and tag_path == y_path:
                use_as = "[ PixelSizeX & Y ]"
            elif tag_path and tag_path == x_path:
                use_as = "[ PixelSizeX ]"
            elif tag_path and tag_path == y_path:
                use_as = "[ PixelSizeY ]"
                
            if last_category is not None and category != last_category:
                # Add horizontal line separating categories
                tree.insert("", "end", values=("─" * 30, "─" * 30, "─" * 80, ""), tags=("separator",))
            display_category = category if category != last_category else ""
            tree.insert("", "end", values=(display_category, key, value, use_as))
            last_category = category
        else:
            key, value = row
            tree.insert("", "end", values=(key, value))
