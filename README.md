# Open WebUI + Ollama Portable Launcher

A fully portable Windows executable that bundles Ollama and Open WebUI into a single package that can run from a USB drive without leaving traces on the host computer.

## Features

✅ **Fully Portable** - Run from USB drive, no installation needed  
✅ **No System Traces** - All data stored in application folder  
✅ **GPU Accelerated** - Automatic CUDA detection for NVIDIA GPUs  
✅ **Self-Contained** - Includes Ollama binary and Open WebUI  
✅ **Auto-Browser Launch** - Opens WebUI automatically when ready  
✅ **Clean Shutdown** - Proper process cleanup on exit

## Quick Start

### For Users (Windows)

1. Download the latest `OpenWebUI-Ollama-Portable-Windows.zip` from [Releases](../../releases)
2. Extract to your USB drive or any folder
3. Run `OpenWebUI-Ollama-Portable.exe`
4. Browser opens automatically to `http://localhost:3000`
5. Start chatting with AI models!

### For Users (macOS)

1. Download the latest `OpenWebUI-Ollama-Portable-macOS.dmg` from [Releases](../../releases)
2. Open the DMG file
3. Drag `OpenWebUI-Ollama.app` to Applications (or any folder)
4. **First time only**: Right-click the app and select "Open" (bypasses Gatekeeper)
5. Click "Open" in the security dialog
6. Browser opens automatically to `http://localhost:3000`
7. Start chatting with AI models!

### For Developers

#### Prerequisites

- Python 3.11+
- Windows (for building .exe)
- Git

#### Build from Source

```bash
# Clone repository
git clone https://github.com/danielfebrero/openwebui-exe-launcher.git
cd openwebui-exe-launcher

# Install dependencies
pip install -r requirements.txt

# Run directly (development)
python main.py
```

#### Build Executable

**macOS:**

```bash
# Automated build script
./build-macos.sh

# Or manual build
pyinstaller --clean openwebui-portable-macos.spec

# Output: dist/OpenWebUI-Ollama.app
```

**Windows:**

```cmd
# Automated build script
build-windows.bat

# Or manual build
pyinstaller --clean openwebui-portable.spec

# Output: dist\OpenWebUI-Ollama-Portable\
```

**Using GitHub Actions:**

- Push to master branch
- Windows and macOS builds run automatically
- Download artifacts from Actions tab or Releases

## Architecture

### Windows Structure

```text
OpenWebUI-Ollama-Portable/
├── OpenWebUI-Ollama-Portable.exe    # Main launcher
├── ollama.exe                        # Bundled Ollama binary
├── webui_launcher.py                 # Open WebUI startup script
├── _internal/                        # Python runtime & dependencies
├── .ollama/                          # Created at runtime
│   └── models/                       # Downloaded AI models
└── data/                             # Created at runtime
    └── (user data, chats, settings)  # All user data
```

### macOS Structure

```text
OpenWebUI-Ollama.app/
├── Contents/
│   ├── MacOS/
│   │   ├── OpenWebUI-Ollama          # Main executable
│   │   └── ollama                    # Bundled Ollama binary
│   ├── Resources/                    # Python runtime & dependencies
│   └── Info.plist                    # App metadata
├── .ollama/                          # Created next to .app
│   └── models/                       # Downloaded AI models
└── data/                             # Created next to .app
    └── (user data, chats, settings)  # All user data
```

## How It Works

1. **Launcher starts** → Checks for port conflicts (11434, 3000)
2. **Ollama starts** → Serves AI models on port 11434
3. **Open WebUI starts** → Web interface on port 3000
4. **Browser opens** → Automatically navigates to localhost:3000
5. **On exit** → Cleans up all processes gracefully

## Data Storage (Portable)

All data is stored relative to the executable location:

- **Models**: `.ollama/models/` - AI model files
- **User Data**: `data/` - Chats, settings, user accounts

**Total size**: ~10GB+ (depending on models downloaded)

## Troubleshooting

### Port Already in Use

If you see "Port 11434 is already in use":

- Close any existing Ollama instances
- Check Task Manager for `ollama.exe` processes

### Firewall Warnings

Windows Firewall may prompt for access:

- Click "Allow access" for both Private and Public networks
- Required for localhost communication

### Models Not Downloading

First model download takes time:

- Small models (7B): ~4-5 GB, 5-10 minutes
- Large models (70B): ~40+ GB, can take hours
- Check `.ollama/models/` folder for progress

### Application Won't Start

- Ensure you extracted the entire ZIP, not just the .exe
- Run from a location you have write permissions
- Check antivirus isn't blocking execution

## Development Notes

### Fixed Issues

- ✅ Platform-specific binary detection (Windows: `.exe`)
- ✅ PyInstaller frozen executable compatibility
- ✅ Proper exception handling with clear error messages
- ✅ Port conflict detection before starting services
- ✅ Process cleanup on exit (SIGINT, SIGTERM, atexit)
- ✅ Portable data storage (USB-friendly)
- ✅ GitHub Actions workflow (uses `--onedir` for compatibility)
- ✅ Deprecated action replaced (`softprops/action-gh-release@v1`)

### Key Technical Decisions

**Why `--onedir` instead of `--onefile`?**

- Better compatibility with complex Python packages (open-webui)
- Faster startup time
- Easier to debug
- Still portable as a folder

**Why `--console` instead of `--windowed`?**

- User can see startup progress
- Error messages are visible
- Debug information accessible
- Better for troubleshooting

**Why separate `webui_launcher.py`?**

- Cannot use `sys.executable -m open_webui` in frozen exe
- Bundled script provides proper entry point
- Allows custom arguments and error handling

## Environment Variables

The launcher automatically sets:

```python
OLLAMA_MODELS={app_dir}/.ollama/models  # Portable model storage
OLLAMA_DEBUG=0                          # Set to "1" for GPU logs
DATA_DIR={app_dir}/data                 # Open WebUI data
OLLAMA_API_BASE=http://localhost:11434  # Ollama endpoint
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Windows
5. Submit a pull request

## License

This project is a launcher/wrapper. Component licenses:

- [Ollama](https://github.com/ollama/ollama) - MIT License
- [Open WebUI](https://github.com/open-webui/open-webui) - MIT License

## Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

## Roadmap

- [x] Support for macOS builds (.app bundles)
- [x] Support for Windows builds (.exe)
- [ ] Support for Linux builds (AppImage)
- [ ] Model preloading in build process
- [ ] Custom port configuration
- [ ] Auto-update functionality
- [ ] Model management UI integration
- [ ] Code signing for macOS and Windows

---

## Made with ❤️ for portable AI
