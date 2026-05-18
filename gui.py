#!/usr/bin/env python3
"""
tifDebloat GUI - Cross-platform (Windows/Linux) UI for TIFF debloating tool.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import tkinter.ttk as ttk
import os
import sys
from pathlib import Path
import threading
import json

# Import the conversion function
from convert_tif import convert_and_compress


class TiffConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("tifDebloat - TIFF Debloater")
        self.root.geometry("750x900")
        self.root.resizable(True, True)
        
        self.input_path = tk.StringVar()
        self.output_mode = tk.StringVar(value="suffix")
        self.output_value = tk.StringVar(value="_gray_compressed")
        self.compression_type = tk.StringVar(value="zlib")
        self.is_converting = False
        self.cancel_requested = False
        self.conversion_thread = None
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Build the UI layout."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== INPUT SECTION =====
        input_frame = ttk.LabelFrame(main_frame, text="Input", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Image or Folder:").pack(anchor=tk.W)
        input_row = ttk.Frame(input_frame)
        input_row.pack(fill=tk.X, pady=5)
        
        self.input_entry = ttk.Entry(input_row, textvariable=self.input_path)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(input_row, text="Browse File", command=self._browse_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(input_row, text="Browse Folder", command=self._browse_folder).pack(side=tk.LEFT, padx=2)
        
        # ===== OUTPUT SECTION =====
        output_frame = ttk.LabelFrame(main_frame, text="Output Options", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        # Radio buttons for output mode
        mode_frame = ttk.Frame(output_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(
            mode_frame, text="Add Suffix",
            variable=self.output_mode, value="suffix",
            command=self._on_mode_change
        ).pack(anchor=tk.W, pady=3)
        
        ttk.Radiobutton(
            mode_frame, text="Save to Output Folder",
            variable=self.output_mode, value="folder",
            command=self._on_mode_change
        ).pack(anchor=tk.W, pady=3)
        
        ttk.Radiobutton(
            mode_frame, text="Replace Original",
            variable=self.output_mode, value="replace",
            command=self._on_mode_change
        ).pack(anchor=tk.W, pady=3)
        
        # Output value input
        self.output_label = ttk.Label(output_frame, text="Suffix (e.g., '_gray_compressed'):")
        self.output_label.pack(anchor=tk.W, pady=(10, 0))
        
        output_row = ttk.Frame(output_frame)
        output_row.pack(fill=tk.X, pady=5)
        
        self.output_entry = ttk.Entry(output_row, textvariable=self.output_value, width=40)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.browse_output_btn = ttk.Button(output_row, text="Browse", command=self._browse_output_folder)
        self.browse_output_btn.pack(side=tk.LEFT)
        self.browse_output_btn.config(state=tk.DISABLED)  # Only enabled for "folder" mode
        
        # ===== COMPRESSION SECTION =====
        compression_frame = ttk.LabelFrame(main_frame, text="Compression Method", padding="10")
        compression_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(
            compression_frame, text="No Compression (larger file size)",
            variable=self.compression_type, value="none"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            compression_frame, text="ZIP/Deflate (recommended, good compression)",
            variable=self.compression_type, value="zlib"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Radiobutton(
            compression_frame, text="LZW (alternative compression)",
            variable=self.compression_type, value="lzw"
        ).pack(anchor=tk.W, pady=2)
        
        # ===== BUTTONS SECTION =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.convert_btn = ttk.Button(button_frame, text="Convert", command=self._start_conversion)
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._request_cancel, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT, padx=5)
        
        # ===== PROGRESS SECTION =====
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="black")
        self.status_label.pack(anchor=tk.W, pady=2)
        
        # ===== LOG SECTION =====
        log_frame = ttk.LabelFrame(main_frame, text="Conversion Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _on_mode_change(self):
        """Update UI based on selected output mode."""
        mode = self.output_mode.get()
        if mode == "suffix":
            self.output_label.config(text="Suffix (e.g., '_gray_compressed'):")
            self.output_entry.config(state=tk.NORMAL)
            self.browse_output_btn.config(state=tk.DISABLED)
            self.output_value.set("_gray_compressed")
        elif mode == "folder":
            self.output_label.config(text="Output Folder:")
            self.output_entry.config(state=tk.NORMAL)
            self.browse_output_btn.config(state=tk.NORMAL)
            self.output_value.set("")
        elif mode == "replace":
            self.output_label.config(text="Replace Original (no further options needed)")
            self.output_entry.config(state=tk.DISABLED)
            self.browse_output_btn.config(state=tk.DISABLED)
            self.output_value.set("")
    
    def _browse_file(self):
        """Open file browser for single TIFF."""
        path = filedialog.askopenfilename(
            title="Select TIFF Image",
            filetypes=[("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        )
        if path:
            self.input_path.set(path)
    
    def _browse_folder(self):
        """Open folder browser."""
        path = filedialog.askdirectory(title="Select Folder with TIFF Images")
        if path:
            self.input_path.set(path)
    
    def _browse_output_folder(self):
        """Open folder browser for output."""
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_value.set(path)
    
    def _log(self, message):
        """Append message to log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _clear_log(self):
        """Clear the log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _update_status(self, message, color="black"):
        """Update status label."""
        self.status_label.config(text=message, foreground=color)
        self.root.update()
    
    def _request_cancel(self):
        """Request cancellation of ongoing conversion."""
        self.cancel_requested = True
        self.cancel_btn.config(state=tk.DISABLED)
        self._update_status("Cancelling...", "orange")
    
    def _start_conversion(self):
        """Start conversion in a background thread."""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input image or folder.")
            return
        
        if self.is_converting:
            messagebox.showwarning("Warning", "Conversion already in progress.")
            return
        
        # Preview: count files before starting
        input_path = Path(self.input_path.get())
        if input_path.is_file():
            file_count = 1
        elif input_path.is_dir():
            files = sorted(input_path.rglob("*.tif")) + sorted(input_path.rglob("*.tiff"))
            file_count = len(set(str(fp.resolve()).lower() for fp in files))
        else:
            messagebox.showerror("Error", "Path not found.")
            return
        
        if file_count == 0:
            messagebox.showwarning("Warning", "No TIFF files found.")
            return
        
        # Show preview dialog
        preview_msg = f"Found {file_count} TIFF file(s) to process.\n\nNote: Non-RGB (grayscale) files will be skipped.\n\nProceed?"
        if not messagebox.askyesno("File Count Preview", preview_msg):
            return
        
        self.is_converting = True
        self.cancel_requested = False
        self.convert_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self._clear_log()
        
        # Run conversion in background thread
        self.conversion_thread = threading.Thread(target=self._conversion_worker)
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
    
    def _conversion_worker(self):
        """Background worker for conversion."""
        try:
            input_path = Path(self.input_path.get())
            mode = self.output_mode.get()
            output_value = self.output_value.get()
            compression = self.compression_type.get()
            
            self._log(f"Starting conversion...")
            self._log(f"Input: {input_path}")
            self._log(f"Mode: {mode}")
            compression_desc = {"none": "Uncompressed", "zlib": "ZIP/Deflate", "lzw": "LZW"}[compression]
            self._log(f"Compression: {compression_desc}\n")
            
            # Determine input files
            if input_path.is_file():
                files = [input_path]
                root_dir = input_path.parent
            elif input_path.is_dir():
                files = sorted(input_path.rglob("*.tif")) + sorted(input_path.rglob("*.tiff"))
                files = sorted({str(file_path.resolve()).lower(): file_path for file_path in files}.values(), key=lambda path: str(path).lower())
                root_dir = input_path
            else:
                self._log(f"Error: Path not found: {input_path}")
                self._update_status("Error: Path not found", "red")
                self.is_converting = False
                self.convert_btn.config(state=tk.NORMAL)
                self.cancel_btn.config(state=tk.DISABLED)
                return
            
            if not files:
                self._log("No TIFF files found.")
                self._update_status("No TIFF files found", "orange")
                self.is_converting = False
                self.convert_btn.config(state=tk.NORMAL)
                self.cancel_btn.config(state=tk.DISABLED)
                return
            
            self._log(f"Found {len(files)} file(s) to process.\n")
            
            converted_count = 0
            skipped_count = 0
            for idx, file_path in enumerate(files):
                # Check for cancellation
                if self.cancel_requested:
                    self._log(f"\n⊘ Conversion cancelled by user. {converted_count} converted, {skipped_count} skipped.")
                    self._update_status(f"Cancelled: {converted_count} converted, {skipped_count} skipped", "orange")
                    break
                
                relative_path = file_path.relative_to(root_dir)
                self._update_status(f"Converting {idx + 1} of {len(files)}: {relative_path}", "blue")
                
                # Determine output path
                if mode == "suffix":
                    relative_parent = file_path.parent.relative_to(root_dir)
                    output_dir = file_path.parent if input_path.is_file() else root_dir / relative_parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / f"{file_path.stem}{output_value}{file_path.suffix}"
                elif mode == "folder":
                    output_folder = Path(output_value)
                    relative_parent = file_path.parent.relative_to(root_dir)
                    output_dir = output_folder if input_path.is_file() else output_folder / relative_parent
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / file_path.name
                elif mode == "replace":
                    # Temporarily save to a temp file, then replace
                    temp_path = file_path.parent / f"{file_path.stem}_temp{file_path.suffix}"
                    output_path = temp_path
                else:
                    output_path = file_path
                
                self._log(f"[{idx + 1}/{len(files)}] {relative_path}")
                
                try:
                    result = convert_and_compress(str(file_path), str(output_path), compression=compression)
                    
                    if result['skipped']:
                        self._log(f"  ⊘ Skipped: {result['reason']}")
                        skipped_count += 1
                    elif result['success']:
                        # If replace mode, swap files
                        if mode == "replace":
                            file_path.unlink()
                            output_path.rename(file_path)
                            self._log(f"  ✓ Replaced original")
                        else:
                            self._log(f"  ✓ Success")
                        
                        converted_count += 1
                        self.progress_var.set((converted_count / len(files)) * 100)
                    else:
                        self._log(f"  ✗ Error: {result['reason']}")
                except Exception as e:
                    self._log(f"  ✗ Error: {e}")
            
            total_processed = converted_count + skipped_count
            self._log(f"\n✓ Complete! {converted_count}/{total_processed} converted, {skipped_count} skipped.")
            self._update_status(f"Done: {converted_count}/{total_processed} converted, {skipped_count} skipped", "green")
            self.progress_var.set(100)
        
        except Exception as e:
            self._log(f"Fatal error: {e}")
            self._update_status("Error during conversion", "red")
        
        finally:
            self.is_converting = False
            self.convert_btn.config(state=tk.NORMAL)
            self.cancel_btn.config(state=tk.DISABLED)
    
    def _save_settings(self):
        """Save UI settings to a JSON file."""
        settings = {
            "input_path": self.input_path.get(),
            "output_mode": self.output_mode.get(),
            "output_value": self.output_value.get(),
            "compression_type": self.compression_type.get(),
        }
        try:
            with open("gui_settings.json", "w") as f:
                json.dump(settings, f)
        except Exception:
            pass
    
    def _load_settings(self):
        """Load UI settings from JSON file."""
        try:
            if os.path.exists("gui_settings.json"):
                with open("gui_settings.json", "r") as f:
                    settings = json.load(f)
                    if "input_path" in settings:
                        self.input_path.set(settings["input_path"])
                    if "output_mode" in settings:
                        self.output_mode.set(settings["output_mode"])
                        self._on_mode_change()
                    if "output_value" in settings:
                        self.output_value.set(settings["output_value"])
                    if "compression_type" in settings:
                        self.compression_type.set(settings["compression_type"])
        except Exception:
            pass
    
    def run(self):
        """Start the GUI."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _on_closing(self):
        """Handle window close event."""
        self._save_settings()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TiffConverterGUI(root)
    app.run()
