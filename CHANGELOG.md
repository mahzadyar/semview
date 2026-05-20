# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-05-20
### Added
- Checkbox-based selection in the directory browser to select multiple files or folders for batch processing.
- Custom `DatabarHeight` mapping: right-click any row in the Extra Tags table and map it as `DatabarHeight` using the context menu.
- Added modern custom composite icons (folder/file with checkbox indicators).
- Re-designed the default TIFF icon to use an image-themed icon.
- Dynamic `Use As` indicator column support for combined mapped tags (e.g. `[ PixelSizeX & DatabarHeight ]`).

### Changed
- Renamed the process button to "Process".
- Configured directory browser default to system logical drives ("This PC" on Windows and `/` on Linux) if no saved history exists.
- Updated GUI title to `SEMView - SEM TIFF Image Processing & Metadata Utility`.

### Fixed
- Fixed unresponsive clicks on directory browser checkboxes via element-based event routing.
- Restored missing `_is_tiff_file` helper function preventing crashes during browser scanning.

## [2.0.0] - 2026-05-20
### Added
- Unified graphical interface: Integrated the image viewer, metadata analyzer, and batch converter into a single `gui.py` application.
- Added explicit UI options to toggle "Skip Color Images" and "Force RGB to Grayscale" for maximum flexibility.
- File Browser tree now dynamically supports selecting a single file or a whole directory for batch conversion.
- Added 8-bit downsampling normalization for processing high bit-depth files (e.g. 16-bit or 32-bit images).
- Customizable metadata assignment: select any row in the Extra Tags table and dynamically map it as `PixelSizeX` or `PixelSizeY` using a context menu.
- Organized settings layout categorizing options under Compression, Manipulation, and Save sections.

### Changed
- `utils/gui_metadata.py` has been fully merged into `gui.py` and removed.
- Refactored `convert_and_compress` mathematically separating grayscale preservation from purely compression logic.
- Consolidated the build pipeline: replaced separate Linux and Windows workflows with a single, optimized GitHub Action `build.yml`.
- Updated default fallback suffix tag to `_processed`.
- Documentation unified into a single `README.md`.

## [1.2.0] - 2026-05-18
### Added
- Folder browser in the GUI with lazy directory loading and click-to-load TIFFs.
- Table-based metadata viewer (Category / Key / Value) replacing the tree view for easier scanning.
- INI-format parsing for proprietary tags (e.g., `FEI_HELIOS`) so instrument metadata displays hierarchically.
- Live preview scaling: preview image now fits the preview panel and redraws on resize.

### Changed
- Metadata decoding logic extended to detect and parse JSON and INI payloads.
- Improved tag preservation and generic handling for complex proprietary TIFF tags.
- CI: `build-linux` workflow now runs tests (if dev deps present), smoke-imports the GUI module, and builds the GUI spec if present.

### Fixes
- Fixed preview downscaling to use real resizing (Pillow) so previews never exceed panel bounds.
- UI: swapped Extra Tags to a practical, grouped table view and added basic Key/Value table.

### Packaging
- PyInstaller specs updated to include GUI artifacts; CI packages `dist` artifacts into the release bundle.

[Unreleased]: #
