#!/usr/bin/env python3
"""
Unified SEMView GUI
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import sys
from pathlib import Path
import threading
import json
from typing import Any, Optional, Dict, Tuple

try:
    import tifffile
    import numpy as np
    from PIL import Image, ImageTk
except ImportError as e:
    raise ImportError(f"Required dependency missing: {e}. Install with: pip install -r requirements.txt") from e

from core.convert_tif import convert_and_compress

from core.metadata import BASIC_TAGS, parse_ini, decode_value, get_databar_height_from_metadata
from core.image_processing import normalize_image, downscale_image
from ui.metadata_panel import format_table_value, flatten_metadata_rows, populate_metadata_table
from ui.settings import load_settings, save_settings

class TiffAppGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SEMView - Unified GUI")
        self.root.geometry("1400x900")
        
        # UI state variables
        self.output_mode = tk.StringVar(value="Suffix")
        self.output_value = tk.StringVar(value="_processed")
        self.compression_type = tk.StringVar(value="zlib")
        
        self.rgb_to_gray_var = tk.BooleanVar(value=True)
        self.bit_depth_var = tk.StringVar(value="original")
        self.update_resolution_var = tk.BooleanVar(value=True)
        self.x_res_tag_path = tk.StringVar(value="FEI_HELIOS / Scan / PixelWidth")
        self.y_res_tag_path = tk.StringVar(value="FEI_HELIOS / Scan / PixelHeight")
        
        self.crop_databar_var = tk.BooleanVar(value=False)
        self.databar_pos_var = tk.StringVar(value="bottom")
        self.databar_height_mode_var = tk.StringVar(value="auto")
        self.databar_height_manual_var = tk.StringVar(value="119")
        self.current_databar_height_cached: Optional[int] = None
        
        # Worker state
        self.is_converting = False
        self.cancel_requested = False
        self.conversion_thread = None

        # Viewer state
        self.current_file: Optional[str] = None
        self.browser_root: Optional[str] = None
        self.photo_image: Optional[ImageTk.PhotoImage] = None
        self._current_preview_image: Optional[np.ndarray] = None
        self._preview_resize_job: Optional[str] = None
        self._browser_item_paths: Dict[str, str] = {}
        self._browser_loaded_dirs: set[str] = set()
        
        self._init_icons()
        self._setup_ui()
        self._load_settings()

    def _init_icons(self):
        from PIL import Image, ImageDraw, ImageTk
        
        # Folder Icon (Golden folder)
        folder_img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(folder_img)
        draw.polygon([(2, 2), (7, 2), (9, 5), (2, 5)], fill="#DDA010")
        try:
            draw.rounded_rectangle([1, 4, 14, 13], radius=1, fill="#FFCA28", outline="#DDA010", width=1)
        except AttributeError:
            draw.rectangle([1, 4, 14, 13], fill="#FFCA28", outline="#DDA010", width=1)
        self.folder_icon = ImageTk.PhotoImage(folder_img)
        
        # File Icon (Sleek document image)
        file_img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(file_img)
        try:
            draw.rounded_rectangle([2, 1, 13, 14], radius=1, fill="#FFFFFF", outline="#78909C", width=1)
        except AttributeError:
            draw.rectangle([2, 1, 13, 14], fill="#FFFFFF", outline="#78909C", width=1)
        draw.polygon([(9, 2), (12, 5), (9, 5)], fill="#78909C")
        draw.line([5, 7, 11, 7], fill="#1E88E5", width=1)
        draw.line([5, 9, 11, 9], fill="#1E88E5", width=1)
        draw.line([5, 11, 9, 11], fill="#1E88E5", width=1)
        self.file_icon = ImageTk.PhotoImage(file_img)

    def _setup_ui(self):
        top_h_paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        top_h_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_v_paned = ttk.Panedwindow(top_h_paned, orient=tk.VERTICAL, width=700)
        top_h_paned.add(left_v_paned, weight=1)
        
        right_v_paned = ttk.Panedwindow(top_h_paned, orient=tk.VERTICAL, width=700)
        top_h_paned.add(right_v_paned, weight=1)
        
        # LEFT V PANED
        browser_frame = ttk.LabelFrame(left_v_paned, text="Folder Browser", padding=5)
        preview_frame = ttk.LabelFrame(left_v_paned, text="Image Preview", padding=5)
        
        left_v_paned.add(browser_frame, weight=1)
        left_v_paned.add(preview_frame, weight=2)
        self.preview_frame = preview_frame
        
        # RIGHT V PANED
        options_frame = ttk.LabelFrame(right_v_paned, text="Process Options", padding=5)
        metadata_frame = ttk.LabelFrame(right_v_paned, text="Metadata", padding=5)
        bottom_frame = ttk.Frame(right_v_paned)
        
        right_v_paned.add(options_frame, weight=0)
        right_v_paned.add(metadata_frame, weight=2)
        right_v_paned.add(bottom_frame, weight=1)
        
        # BROWSER
        browser_toolbar = ttk.Frame(browser_frame)
        browser_toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        ttk.Button(browser_toolbar, text="Set Root Folder", command=self._browse_folder).pack(side=tk.LEFT)
        self.browser_path_label = ttk.Label(browser_toolbar, text="No folder selected", anchor="w")
        self.browser_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        browser_tree_frame = ttk.Frame(browser_frame)
        browser_tree_frame.pack(fill=tk.BOTH, expand=True)

        self.browser_tree = ttk.Treeview(browser_tree_frame, show="tree")
        browser_scroll = ttk.Scrollbar(browser_tree_frame, orient=tk.VERTICAL, command=self.browser_tree.yview)
        self.browser_tree.configure(yscrollcommand=lambda first, last, sb=browser_scroll: sb.set(first, last))
        self.browser_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        browser_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.browser_tree.bind("<<TreeviewOpen>>", self._on_browser_open)
        self.browser_tree.bind("<<TreeviewSelect>>", self._on_browser_select)

        # PREVIEW
        self.image_label = tk.Label(preview_frame, bg="gray20", relief=tk.SUNKEN)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        self.image_label.bind("<Configure>", self._schedule_preview_redraw)

        # COMPRESSION SECTION
        comp_lf = ttk.LabelFrame(options_frame, text="Compression")
        comp_lf.pack(fill=tk.X, pady=5, padx=2)
        
        comp_row = ttk.Frame(comp_lf)
        comp_row.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Checkbutton(comp_row, text="Non-colored RGB to grayscale", variable=self.rgb_to_gray_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(comp_row, text="Method:").pack(side=tk.LEFT, padx=2)
        comp_combo = ttk.Combobox(comp_row, textvariable=self.compression_type, values=("none", "zlib", "lzw"), state="readonly", width=8)
        comp_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(comp_row, text="Bit Depth:").pack(side=tk.LEFT, padx=2)
        bit_combo = ttk.Combobox(comp_row, textvariable=self.bit_depth_var, values=("original", "8-bit"), state="readonly", width=8)
        bit_combo.pack(side=tk.LEFT, padx=2)

        # MANIPULATION SECTION
        man_lf = ttk.LabelFrame(options_frame, text="Manipulation")
        man_lf.pack(fill=tk.X, pady=5, padx=2)
        
        # Row 1: Crop Databar
        crop_row = ttk.Frame(man_lf)
        crop_row.pack(fill=tk.X, pady=2, padx=5)
        
        ttk.Checkbutton(crop_row, text="Crop Databar", variable=self.crop_databar_var, command=self._on_crop_toggle).pack(side=tk.LEFT, padx=(0, 10))
        
        self.crop_settings_frame = ttk.Frame(crop_row)
        self.crop_settings_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(self.crop_settings_frame, text="Pos:").pack(side=tk.LEFT, padx=2)
        self.crop_pos_bottom = ttk.Radiobutton(self.crop_settings_frame, text="Bottom", variable=self.databar_pos_var, value="bottom", command=self._on_crop_param_change)
        self.crop_pos_bottom.pack(side=tk.LEFT, padx=2)
        self.crop_pos_top = ttk.Radiobutton(self.crop_settings_frame, text="Top", variable=self.databar_pos_var, value="top", command=self._on_crop_param_change)
        self.crop_pos_top.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(self.crop_settings_frame, text="Height:").pack(side=tk.LEFT, padx=(10, 2))
        self.crop_height_auto = ttk.Radiobutton(self.crop_settings_frame, text="Auto", variable=self.databar_height_mode_var, value="auto", command=self._on_crop_param_change)
        self.crop_height_auto.pack(side=tk.LEFT, padx=2)
        self.crop_height_manual = ttk.Radiobutton(self.crop_settings_frame, text="Manual", variable=self.databar_height_mode_var, value="manual", command=self._on_crop_param_change)
        self.crop_height_manual.pack(side=tk.LEFT, padx=2)
        
        self.crop_height_entry = ttk.Entry(self.crop_settings_frame, textvariable=self.databar_height_manual_var, width=5)
        self.crop_height_entry.pack(side=tk.LEFT, padx=2)
        self.databar_height_manual_var.trace_add("write", lambda *args: self._on_crop_param_change())
        
        # Row 2: Metadata
        meta_row = ttk.Frame(man_lf)
        meta_row.pack(fill=tk.X, pady=2, padx=5)
        ttk.Checkbutton(meta_row, text="Update Resolution", variable=self.update_resolution_var).pack(side=tk.LEFT, padx=0)

        # SAVE SECTION
        save_lf = ttk.LabelFrame(options_frame, text="Save")
        save_lf.pack(fill=tk.X, pady=5, padx=2)
        
        save_row = ttk.Frame(save_lf)
        save_row.pack(fill=tk.X, pady=5, padx=5)
        
        self.output_mode_combo = ttk.Combobox(
            save_row, 
            textvariable=self.output_mode, 
            values=("Suffix", "Save as different folder", "Replace"), 
            state="readonly", 
            width=22
        )
        self.output_mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.output_mode_combo.bind("<<ComboboxSelected>>", lambda e: self._on_mode_change())
        
        # Dynamic container for save settings
        self.save_dynamic_frame = ttk.Frame(save_row)
        self.save_dynamic_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.output_label = ttk.Label(self.save_dynamic_frame, text="Suffix:")
        self.output_label.pack(side=tk.LEFT, padx=2)
        
        self.output_entry = ttk.Entry(self.save_dynamic_frame, textvariable=self.output_value, width=15)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.browse_output_btn = ttk.Button(self.save_dynamic_frame, text="Browse", command=self._browse_output_folder)
        self.browse_output_btn.pack(side=tk.LEFT, padx=2)
        
        self.replace_warn_label = ttk.Label(self.save_dynamic_frame, text="⚠️ Warning: This will overwrite original files!", foreground="red")
        
        # Buttons Row inside Save section
        btn_row = ttk.Frame(save_lf)
        btn_row.pack(fill=tk.X, pady=(2, 5), padx=5)
        self.convert_btn = ttk.Button(btn_row, text="Convert Selected", command=self._start_conversion)
        self.convert_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.cancel_btn = ttk.Button(btn_row, text="Cancel", command=self._request_cancel, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)

        # RIGHT: METADATA
        self.notebook = ttk.Notebook(metadata_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Basic metadata tab
        basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(basic_frame, text="Basic Info")
        self.basic_tree = ttk.Treeview(basic_frame, height=20, columns=("key", "value"), show="headings")
        self.basic_tree.heading("key", text="Key")
        self.basic_tree.heading("value", text="Value")
        self.basic_tree.column("key", anchor="w", width=150, stretch=False)
        self.basic_tree.column("value", anchor="w", stretch=True)
        scrollbar = ttk.Scrollbar(basic_frame, orient=tk.VERTICAL, command=self.basic_tree.yview)
        self.basic_tree.configure(yscrollcommand=lambda first, last, sb=scrollbar: sb.set(first, last))
        self.basic_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Extra tags tab
        extra_frame = ttk.Frame(self.notebook)
        self.notebook.add(extra_frame, text="Extra Tags")
        self.extra_tree = ttk.Treeview(extra_frame, height=20, columns=("category", "key", "value", "use_as"), show="headings")
        self.extra_tree.heading("category", text="Category")
        self.extra_tree.heading("key", text="Key")
        self.extra_tree.heading("value", text="Value")
        self.extra_tree.heading("use_as", text="Use As")
        self.extra_tree.column("category", anchor="w", width=150, stretch=False)
        self.extra_tree.column("key", anchor="w", width=150, stretch=False)
        self.extra_tree.column("value", anchor="w", stretch=True)
        self.extra_tree.column("use_as", anchor="center", width=120, stretch=False)
        
        self.extra_tree.bind("<ButtonRelease-1>", self._on_extra_tree_click)
        
        # Context menu for assigning tags
        self.extra_tree_menu = tk.Menu(self.root, tearoff=0)
        self.extra_tree_menu.add_command(label="Use as PixelSizeX (Width)", command=lambda: self._set_resolution_tag("x"))
        self.extra_tree_menu.add_command(label="Use as PixelSizeY (Height)", command=lambda: self._set_resolution_tag("y"))
        self.extra_tree_menu.add_command(label="Use as Both (PixelSizeX & Y)", command=lambda: self._set_resolution_tag("both"))
        self.extra_tree_menu.add_separator()
        self.extra_tree_menu.add_command(label="Clear Assignment", command=lambda: self._set_resolution_tag("clear"))
        scrollbar2 = ttk.Scrollbar(extra_frame, orient=tk.VERTICAL, command=self.extra_tree.yview)
        self.extra_tree.configure(yscrollcommand=lambda first, last, sb=scrollbar2: sb.set(first, last))
        self.extra_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        self.extra_tree.tag_configure("separator", foreground="#A0A0A0")

        # BOTTOM: PROGRESS AND LOG
        progress_frame = ttk.Frame(bottom_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="black")
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

        log_frame = ttk.Frame(bottom_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._on_mode_change() # Init correct states
    
    def _on_extra_tree_click(self, event):
        region = self.extra_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.extra_tree.identify_column(event.x)
            # Column #4 is 'use_as'
            if column == "#4":
                self.extra_tree.selection_set(self.extra_tree.identify_row(event.y))
                self.extra_tree_menu.post(event.x_root, event.y_root)

    def _set_resolution_tag(self, target: str):
        selection = self.extra_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        values = self.extra_tree.item(item_id, "values")
        if not values or len(values) < 4:
            return
            
        # Values are (category, key, value, use_as)
        category = values[0].strip()
        key = values[1].strip()
        
        # Build the path exactly as UI formats it
        if category and key:
            tag_path = f"{category} / {key}"
        else:
            tag_path = category or key
            
        if target == "x":
            self.x_res_tag_path.set(tag_path)
            if self.y_res_tag_path.get() == tag_path:
                self.y_res_tag_path.set("")
        elif target == "y":
            self.y_res_tag_path.set(tag_path)
            if self.x_res_tag_path.get() == tag_path:
                self.x_res_tag_path.set("")
        elif target == "both":
            self.x_res_tag_path.set(tag_path)
            self.y_res_tag_path.set(tag_path)
        elif target == "clear":
            if self.x_res_tag_path.get() == tag_path:
                self.x_res_tag_path.set("")
            if self.y_res_tag_path.get() == tag_path:
                self.y_res_tag_path.set("")
                
        # Re-render the metadata to update the 'Use As' column display
        if self.current_file:
            try:
                self._load_and_display(self.current_file)
            except Exception:
                pass

    def _on_mode_change(self):
        mode = self.output_mode.get()
        
        # Hide all dynamic widgets first
        self.output_label.pack_forget()
        self.output_entry.pack_forget()
        self.browse_output_btn.pack_forget()
        self.replace_warn_label.pack_forget()
        
        if mode == "Suffix":
            self.output_label.config(text="Suffix:")
            self.output_label.pack(side=tk.LEFT, padx=2)
            self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            # Reset folder path to standard suffix if it has directory markers
            curr_val = self.output_value.get()
            if not curr_val or ":" in curr_val or "/" in curr_val or "\\" in curr_val:
                self.output_value.set("_processed")
        elif mode == "Save as different folder":
            self.output_label.config(text="Folder:")
            self.output_label.pack(side=tk.LEFT, padx=2)
            self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            self.browse_output_btn.pack(side=tk.LEFT, padx=2)
            # Clear suffix values
            curr_val = self.output_value.get()
            if curr_val.startswith("_"):
                self.output_value.set("")
        elif mode == "Replace":
            self.replace_warn_label.pack(side=tk.LEFT, padx=2)
    
    def _browse_output_folder(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_value.set(path)
    
    def _log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _update_status(self, message, color="black"):
        self.status_label.config(text=message, foreground=color)
        self.root.update()

    def _browse_folder(self):
        initial_dir = self.browser_root
        if initial_dir is None and self.current_file:
            initial_dir = os.path.dirname(self.current_file)
        if initial_dir is None:
            initial_dir = os.path.dirname(os.path.abspath(__file__))
        folder_path = filedialog.askdirectory(title="Select a folder", initialdir=initial_dir)
        if folder_path:
            self._set_browser_root(folder_path)

    def _set_browser_root(self, folder_path: str):
        folder_path = os.path.abspath(folder_path)
        if not os.path.isdir(folder_path): return
        self.browser_root = folder_path
        self.browser_path_label.config(text=folder_path)
        for item in self.browser_tree.get_children():
            self.browser_tree.delete(item)
        self._browser_item_paths.clear()
        self._browser_loaded_dirs.clear()
        root_text = os.path.basename(folder_path) or folder_path
        root_id = self.browser_tree.insert("", "end", text=root_text, open=True, image=self.folder_icon)
        self._browser_item_paths[root_id] = folder_path
        self._populate_browser_dir(root_id, folder_path)
        self.browser_tree.selection_set(root_id)
        self.browser_tree.focus(root_id)

    def _populate_browser_dir(self, parent_id: str, dir_path: str):
        if dir_path in self._browser_loaded_dirs: return
        self._browser_loaded_dirs.add(dir_path)
        try:
            entries = sorted(os.scandir(dir_path), key=lambda entry: (not entry.is_dir(), entry.name.lower()))
        except OSError:
            return
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                node_id = self.browser_tree.insert(parent_id, "end", text=entry.name, open=False, image=self.folder_icon)
                self._browser_item_paths[node_id] = entry.path
                self.browser_tree.insert(node_id, "end", text="Loading...", tags=("placeholder",))
            elif entry.is_file(follow_symlinks=False) and self._is_tiff_file(entry.name):
                node_id = self.browser_tree.insert(parent_id, "end", text=entry.name, open=False, image=self.file_icon)
                self._browser_item_paths[node_id] = entry.path

    def _is_tiff_file(self, filename: str) -> bool:
        ln = filename.lower()
        return ln.endswith(".tif") or ln.endswith(".tiff")

    def _on_browser_open(self, event: Any):
        item_id = self.browser_tree.focus()
        if not item_id: return
        item_path = self._browser_item_paths.get(item_id)
        if not item_path or not os.path.isdir(item_path): return
        children = self.browser_tree.get_children(item_id)
        if len(children) == 1:
            first_child = children[0]
            if "placeholder" in self.browser_tree.item(first_child, "tags"):
                self.browser_tree.delete(first_child)
        self._populate_browser_dir(item_id, item_path)

    def _on_browser_select(self, event: Any):
        item_id = self.browser_tree.focus()
        if not item_id: return
        item_path = self._browser_item_paths.get(item_id)
        if not item_path or not os.path.isfile(item_path): return
        if not self._is_tiff_file(item_path): return
        if item_path != self.current_file:
            try:
                self._load_and_display(item_path)
            except Exception as e:
                pass

    def _load_and_display(self, file_path: str):
        with tifffile.TiffFile(file_path) as tif:
            if len(tif.pages) > 0:
                page = tif.pages[0]
                image_array = page.asarray()
                self.current_databar_height_cached = get_databar_height_from_metadata(page, tif)
                self._display_image_preview(image_array)
                self._display_metadata(page, tif)
        self.current_file = file_path



    def _display_image_preview(self, image_array: np.ndarray):
        self._current_preview_image = image_array
        self._render_current_preview()

    def _schedule_preview_redraw(self, event: Any):
        if self._preview_resize_job is not None:
            try:
                self.root.after_cancel(self._preview_resize_job)
            except Exception:
                pass
        self._preview_resize_job = self.root.after(50, self._render_current_preview)

    def _render_current_preview(self):
        if self._current_preview_image is None: return
        try:
            normalized = normalize_image(self._current_preview_image)
            
            if self.crop_databar_var.get():
                H, W = normalized.shape[:2]
                h_crop = None
                if self.databar_height_mode_var.get() == "auto":
                    h_crop = self.current_databar_height_cached
                else:
                    try:
                        h_crop = int(self.databar_height_manual_var.get())
                    except ValueError:
                        h_crop = 119
                
                if h_crop and 0 < h_crop < H:
                    pos = self.databar_pos_var.get()
                    if pos == "bottom":
                        normalized = normalized[:-h_crop, ...]
                    elif pos == "top":
                        normalized = normalized[h_crop:, ...]
            
            max_width = max(self.image_label.winfo_width() - 10, 200)
            max_height = max(self.image_label.winfo_height() - 10, 200)
            if max_width <= 1 or max_height <= 1:
                max_width, max_height = 400, 400
            downscaled = downscale_image(normalized, max_width, max_height)
            pil_image = Image.fromarray(downscaled, mode="L")
            self.photo_image = ImageTk.PhotoImage(pil_image)
            self.image_label.config(image=self.photo_image)
        except Exception:
            pass

    def _on_crop_toggle(self):
        enabled = self.crop_databar_var.get()
        state = tk.NORMAL if enabled else tk.DISABLED
        
        self.crop_pos_bottom.config(state=state)
        self.crop_pos_top.config(state=state)
        self.crop_height_auto.config(state=state)
        self.crop_height_manual.config(state=state)
        
        if enabled and self.databar_height_mode_var.get() == "manual":
            self.crop_height_entry.config(state=tk.NORMAL)
        else:
            self.crop_height_entry.config(state=tk.DISABLED)
            
        self._render_current_preview()

    def _on_crop_param_change(self):
        enabled = self.crop_databar_var.get()
        if enabled and self.databar_height_mode_var.get() == "manual":
            self.crop_height_entry.config(state=tk.NORMAL)
        else:
            self.crop_height_entry.config(state=tk.DISABLED)
            
        self._render_current_preview()

    def _display_metadata(self, page: Any, tif: Any):
        basic_rows = []
        extra_rows = []
        for tag in page.tags.values():
            tag_code = tag.code
            tag_name = tag.name or f"Tag {tag_code}"
            try:
                if tag_code in BASIC_TAGS:
                    basic_rows.append((BASIC_TAGS[tag_code], format_table_value(tag.value)))
                else:
                    val = tag.value
                    if isinstance(val, dict) or (isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict)):
                        fh = tif.filehandle
                        fh.seek(tag.valueoffset)
                        raw_bytes = fh.read(tag.valuebytecount)
                        decoded = decode_value(raw_bytes)
                    else:
                        decoded = decode_value(val)

                    if isinstance(decoded, dict):
                        extra_rows.extend(flatten_metadata_rows(decoded, tag_name))
                    elif isinstance(decoded, (list, tuple)) and decoded and all(isinstance(item, dict) for item in decoded):
                        for index, item in enumerate(decoded):
                            extra_rows.extend(flatten_metadata_rows(item, f"{tag_name}[{index}]"))
                    else:
                        extra_rows.append((tag_name, "", format_table_value(decoded)))
            except Exception as e:
                extra_rows.append((tag_name, "", f"Error: {e}"))
        populate_metadata_table(self.basic_tree, basic_rows, include_category=False)
        if extra_rows:
            populate_metadata_table(self.extra_tree, extra_rows, include_category=True, 
                                    x_path=self.x_res_tag_path.get(), y_path=self.y_res_tag_path.get())
        else:
            self.extra_tree.insert("", "end", values=("", "", "", "(No extra tags)"))

    def _request_cancel(self):
        self.cancel_requested = True
        self.cancel_btn.config(state=tk.DISABLED)
        self._update_status("Cancelling...", "orange")

    def _start_conversion(self):
        selected_id = self.browser_tree.focus()
        if not selected_id:
            messagebox.showerror("Error", "Please select a file or folder from the browser.")
            return
        
        path_selected = Path(self._browser_item_paths[selected_id])
        
        if self.is_converting:
            messagebox.showwarning("Warning", "Conversion already in progress.")
            return

        if path_selected.is_file():
            file_count = 1
        elif path_selected.is_dir():
            # shallow search for simplicity or rglob. Prompt says deeply or shallowly, I will use rglob
            files = sorted(path_selected.rglob("*.tif")) + sorted(path_selected.rglob("*.tiff"))
            file_count = len(set(str(fp.resolve()).lower() for fp in files))
        else:
            messagebox.showerror("Error", "Path not found.")
            return

        if file_count == 0:
            messagebox.showwarning("Warning", "No TIFF files found.")
            return

        preview_msg = f"Found {file_count} TIFF file(s) to process.\n\nRGB to Grayscale: {self.rgb_to_gray_var.get()}\nCrop Databar: {self.crop_databar_var.get()}\n\nProceed?"
        if not messagebox.askyesno("File Count Preview", preview_msg):
            return

        self.is_converting = True
        self.cancel_requested = False
        self.convert_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self._clear_log()
        
        self.conversion_thread = threading.Thread(target=self._conversion_worker, args=(path_selected,))
        self.conversion_thread.daemon = True
        self.conversion_thread.start()

    def _conversion_worker(self, path_selected: Path):
        try:
            mode_mapping = {
                "Suffix": "suffix",
                "Save as different folder": "folder",
                "Replace": "replace"
            }
            mode = mode_mapping.get(self.output_mode.get(), "suffix")
            output_value = self.output_value.get()
            compression = self.compression_type.get()
            bit_depth = self.bit_depth_var.get()
            
            rgb_to_gray = self.rgb_to_gray_var.get()
            update_resolution = self.update_resolution_var.get()
            x_res_tag = self.x_res_tag_path.get()
            y_res_tag = self.y_res_tag_path.get()
            
            crop_databar = self.crop_databar_var.get()
            databar_pos = self.databar_pos_var.get()
            databar_height_mode = self.databar_height_mode_var.get()
            try:
                databar_height_manual = int(self.databar_height_manual_var.get())
            except ValueError:
                databar_height_manual = 119

            self._log(f"Starting conversion...")
            self._log(f"Input: {path_selected}")
            self._log(f"Mode: {mode}")
            self._log(f"Compression: {compression}")
            self._log(f"Bit Depth: {bit_depth}")
            self._log(f"RGB to Grayscale: {rgb_to_gray}")
            self._log(f"Crop Databar: {crop_databar} ({databar_pos}, {databar_height_mode} height)")
            self._log(f"Update Resolution: {update_resolution}\n")
            
            if path_selected.is_file():
                files = [path_selected]
                root_dir = path_selected.parent
            else:
                files = sorted(path_selected.rglob("*.tif")) + sorted(path_selected.rglob("*.tiff"))
                files = sorted({str(f.resolve()).lower(): f for f in files}.values(), key=lambda path: str(path).lower())
                root_dir = path_selected

            converted_count = 0
            skipped_count = 0
            for idx, file_path in enumerate(files):
                if self.cancel_requested:
                    self._log(f"\n⊘ Conversion cancelled.")
                    break
                
                relative_path = file_path.relative_to(root_dir)
                self._update_status(f"Converting {idx + 1} of {len(files)}: {relative_path}", "blue")
                
                if mode == "suffix":
                    relative_parent = file_path.parent.relative_to(root_dir)
                    output_dir = file_path.parent if path_selected.is_file() else root_dir / relative_parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / f"{file_path.stem}{output_value}{file_path.suffix}"
                elif mode == "folder":
                    output_folder = Path(output_value)
                    relative_parent = file_path.parent.relative_to(root_dir)
                    output_dir = output_folder if path_selected.is_file() else output_folder / relative_parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / file_path.name
                elif mode == "replace":
                    temp_path = file_path.parent / f"{file_path.stem}_temp{file_path.suffix}"
                    output_path = temp_path
                else:
                    output_path = file_path

                self._log(f"[{idx + 1}/{len(files)}] {relative_path}")
                try:
                    result = convert_and_compress(
                        str(file_path), 
                        str(output_path), 
                        compression=compression,
                        rgb_to_grayscale_enabled=rgb_to_gray,
                        bit_depth=bit_depth,
                        crop_databar=crop_databar,
                        databar_position=databar_pos,
                        databar_height_mode=databar_height_mode,
                        databar_height_manual=databar_height_manual,
                        update_resolution=update_resolution,
                        x_res_tag_path=x_res_tag,
                        y_res_tag_path=y_res_tag
                    )
                    
                    if result.get('skipped', False):
                        self._log(f"  ⊘ Skipped: {result.get('reason','')}")
                        skipped_count += 1
                    elif result.get('success', False):
                        if mode == "replace":
                            file_path.unlink()
                            output_path.rename(file_path)
                            self._log(f"  ✓ Replaced original")
                        else:
                            self._log(f"  ✓ Success")
                        converted_count += 1
                        self.progress_var.set((converted_count / len(files)) * 100)
                    else:
                        self._log(f"  ✗ Error: {result.get('reason','')}")
                except Exception as e:
                    self._log(f"  ✗ Error: {e}")
            
            total_processed = converted_count + skipped_count
            self._log(f"\n✓ Complete! {converted_count}/{total_processed} converted, {skipped_count} skipped.")
            self._update_status(f"Done: {converted_count} converted", "green")
            self.progress_var.set(100)
        except Exception as e:
            self._log(f"Fatal error: {e}")
            self._update_status("Error during conversion", "red")
        finally:
            self.is_converting = False
            self.convert_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)

    def _save_settings(self):
        settings = {
            "output_mode": self.output_mode.get(),
            "output_value": self.output_value.get(),
            "compression_type": self.compression_type.get(),
            "bit_depth": self.bit_depth_var.get(),
            "rgb_to_gray": self.rgb_to_gray_var.get(),
            "crop_databar": self.crop_databar_var.get(),
            "databar_position": self.databar_pos_var.get(),
            "databar_height_mode": self.databar_height_mode_var.get(),
            "databar_height_manual": self.databar_height_manual_var.get(),
            "update_resolution": self.update_resolution_var.get(),
            "x_res_tag_path": self.x_res_tag_path.get(),
            "y_res_tag_path": self.y_res_tag_path.get(),
            "browser_root": self.browser_root
        }
        save_settings(settings)
    
    def _load_settings(self):
        settings = load_settings()
        if "output_mode" in settings:
            val = settings["output_mode"]
            # Map old lowercase settings to new combo display values
            old_to_new = {
                "suffix": "Suffix",
                "folder": "Save as different folder",
                "replace": "Replace"
            }
            self.output_mode.set(old_to_new.get(val, val))
        if "output_value" in settings: self.output_value.set(settings["output_value"])
        if "compression_type" in settings: self.compression_type.set(settings["compression_type"])
        if "bit_depth" in settings: self.bit_depth_var.set(settings["bit_depth"])
        if "rgb_to_gray" in settings: self.rgb_to_gray_var.set(settings["rgb_to_gray"])
        if "crop_databar" in settings: self.crop_databar_var.set(settings["crop_databar"])
        if "databar_position" in settings: self.databar_pos_var.set(settings["databar_position"])
        if "databar_height_mode" in settings: self.databar_height_mode_var.set(settings["databar_height_mode"])
        if "databar_height_manual" in settings: self.databar_height_manual_var.set(settings["databar_height_manual"])
        if "update_resolution" in settings: self.update_resolution_var.set(settings["update_resolution"])
        if "x_res_tag_path" in settings: self.x_res_tag_path.set(settings["x_res_tag_path"])
        if "y_res_tag_path" in settings: self.y_res_tag_path.set(settings["y_res_tag_path"])
        if "browser_root" in settings and settings["browser_root"] and os.path.exists(settings["browser_root"]):
            self._set_browser_root(settings["browser_root"])
        self._on_crop_toggle()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _on_closing(self):
        self._save_settings()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TiffAppGUI(root)
    app.run()
