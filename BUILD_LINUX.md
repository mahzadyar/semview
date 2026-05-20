# Building SEMView for Linux

This guide explains how to create a standalone Linux executable for SEMView that runs without requiring Python or dependencies.

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
   chmod +x SEMView
   
   # Run directly
   ./SEMView
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
   pyinstaller semview.spec
   ```

4. **Find your executable:**
   ```bash
   # The executable is in dist/SEMView
   dist/SEMView
   ```

5. **Create a distributable package:**
   ```bash
   # Make it executable
   chmod +x dist/SEMView
   
   # Create tarball for distribution
   tar -czf semview-linux.tar.gz dist/SEMView
   ```

### Run the application:
```bash
./dist/SEMView
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
   chmod +x SEMView
   ```

3. **Test GUI launches:**
   ```bash
   ./SEMView
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
chmod +x SEMView
./SEMView
```

### Issue: "No module named 'tkinter'"
**Solution (on Linux):**
```bash
sudo apt-get install python3-tk
```

### Issue: "GUI doesn't appear or crashes
**Debugging:**
```bash
# Run with console output to see errors
./SEMView 2>&1 | tee debug.log
```

### Issue: "UPX compression failed"
**Solution:** UPX may not support your platform. Edit `semview.spec` and change:
```python
upx=False,  # Disable UPX compression
```

Then rebuild.

---

## Distributing Your Executable

### For Local Use:
1. Create folder: `~/semview_app/`
2. Copy `SEMView` executable
3. Run with: `~/semview_app/SEMView`

### For Distribution (AppImage - Optional):
If you want to distribute across different Linux distributions:

```bash
# Install appimagetool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppImage
./appimagetool-x86_64.AppImage dist/SEMView SEMView.AppImage
chmod +x SEMView.AppImage
```

Then users can simply run: `./SEMView.AppImage`

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

- **GitHub Actions not working?** Check `.github/workflows/build.yml`
- **Build errors?** Review `pyinstaller` warnings in action logs
- **Runtime issues?** Enable debug logging in `gui.py`
