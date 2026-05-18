# Building TIFF Debloater for Linux

This guide explains how to create a standalone Linux executable for the TIFF Debloater that runs without requiring Python or dependencies.

## Option 1: Automated Build with GitHub Actions (Recommended)

### Prerequisites
- GitHub account
- Push code to a GitHub repository

### Steps

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit with PyInstaller setup"
   git remote add origin https://github.com/YOUR_USERNAME/TIFF_comp.git
   git push -u origin main
   ```

2. **Create a release tag to trigger the build:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Monitor the build:**
   - Go to your repository on GitHub
   - Click the "Actions" tab
   - Watch the "Build Linux Executable" workflow
   - Once complete, download the executable from the Release page

4. **Run on Linux Mint:**
   ```bash
   # Make executable
   chmod +x tiff-comp
   
   # Run directly
   ./tiff-comp
   ```

---

## Option 2: Local Build on Linux Mint 22.3

If you prefer to build locally on Linux Mint 22.3:

### Prerequisites
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-tk upx

# Clone or navigate to your project
cd ~/TIFF_comp
```

### Build Steps

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build the executable:**
   ```bash
   pyinstaller tifDebloat.spec
   ```

4. **Find your executable:**
   ```bash
   # The executable is in dist/tifDebloat
   dist/tifDebloat
   ```

5. **Create a distributable package:**
   ```bash
   # Make it executable
   chmod +x dist/tifDebloat
   
   # Create tarball for distribution
   tar -czf tifDebloat-linux.tar.gz dist/tifDebloat
   ```

### Run the application:
```bash
./dist/tifDebloat
```

---

## Option 3: Manual Cross-Compilation (Advanced)

If you need to build on Windows for Linux:

1. **Install PyInstaller on Windows:**
   ```powershell
   pip install pyinstaller
   ```

2. **Install Linux build tools** (using WSL2 or Docker):
   - This is complex and **not recommended**
   - Better to use GitHub Actions or build natively on Linux

---

## Verification & Testing

### On Linux Mint 22.3:

1. **Download the executable** (from GitHub Actions or build locally)

2. **Make it executable:**
   ```bash
   chmod +x tifDebloat
   ```

3. **Test GUI launches:**
   ```bash
   ./tifDebloat
   ```

4. **Test with sample files:**
   - Place RGB TIFF files in the `sample/` folder
   - Use the GUI to select files and convert them
   - Verify output is single-channel compressed grayscale TIFF for files where RGB channels are identical
   - Verify non-identical RGB TIFFs are skipped with a clear log message

5. **Check file integrity:**
   ```bash
   file sample/*.tif
   file output/*.tif
   ```

---

## Troubleshooting

### Issue: "Permission denied" when running executable
**Solution:**
```bash
chmod +x tifDebloat
./tifDebloat
```

### Issue: "No module named 'tkinter'"
**Solution (on Linux):**
```bash
sudo apt-get install python3-tk
```

### Issue: GUI doesn't appear or crashes
**Debugging:**
```bash
# Run with console output to see errors
./tifDebloat 2>&1 | tee debug.log
```

### Issue: "UPX compression failed"
**Solution:** UPX may not support your platform. Edit `tifDebloat.spec` and change:
```python
upx=False,  # Disable UPX compression
```

Then rebuild.

---

## Distributing Your Executable

### For Local Use:
1. Create folder: `~/tifDebloat_app/`
2. Copy `tifDebloat` executable
3. Run with: `~/tifDebloat_app/tifDebloat`

### For Distribution (AppImage - Optional):
If you want to distribute across different Linux distributions:

```bash
# Install appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppImage
./appimagetool-x86_64.AppImage dist/tifDebloat tifDebloat.AppImage
chmod +x TIFF_Comp.AppImage
```

Then users can simply run: `./TIFF_Comp.AppImage`

---

## File Size & Performance

- **Single-file executable:** ~100-150 MB (includes Python runtime + dependencies)
- **First launch:** May take a few seconds as it extracts dependencies
- **Subsequent launches:** Normal speed
- **Memory usage:** Standard for Python/tkinter applications

---

## Version Updates

When you update the code:

1. **Update version in git tag:**
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

2. **GitHub Actions will automatically:**
   - Build new executable
   - Create new Release with updated binary

3. **Users can download** the new version from Releases page

---

## Need Help?

- **GitHub Actions not working?** Check `.github/workflows/build-linux.yml`
- **Build errors?** Review `pyinstaller` warnings in action logs
- **Runtime issues?** Enable debug logging in `gui.py`
