# Changelog

All notable changes to this project will be documented in this file.

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
