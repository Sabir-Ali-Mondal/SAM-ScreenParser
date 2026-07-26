# SAM ScreenParser

**Note on Naming:** In this project, **SAM** stands for **S**creen **A**utomation **M**anager (and is also a nod to the author's initials, **S**abir **A**li **M**ondal).
*This project is entirely independent and is NOT related to Meta's Segment Anything Model (SAM).*

## Project Overview

SAM ScreenParser is a local, CPU-friendly pipeline that converts the live screen into structured, deterministic data for desktop automation agents. In a single pass it captures the screenshot, the active window, the screen state, every actionable UI element with pixel-perfect coordinates and clean text, and the current cursor position with the real control underneath it. It runs entirely offline on standard laptops with no cloud APIs and no dedicated GPU.

What it guarantees:

- Pixel-perfect coordinates from Florence-2 vision grounding, mapped to the image's true pixel size, so detection is resolution-independent.
- Clean text from Tesseract OCR with contrast normalization and icon-garbage removal.
- DPI-aware capture so detection coordinates, UIA coordinates, cursor coordinates, and click coordinates all agree on scaled displays.
- A confidence score on every element so a controller can refuse to act on uncertain data.
- A cursor snapshot that anchors the controller to the real control under the pointer.

What it does not guarantee, by design: it declines to act on elements it cannot classify with confidence rather than click the wrong target. That refusal is a feature, not a gap.

For architecture, full setup, the control-safe schema, and the rules a controller must follow, see [technical_documentation.md](https://github.com/Sabir-Ali-Mondal/SAM-ScreenParser/blob/main/technical_documentation.md).

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation
py screen_analyzer.py
```

## License and Credits

- Florence-2: Microsoft Research (Apache 2.0)
- Tesseract OCR: Google Open Source (Apache 2.0)
- OpenCV: OpenCV Team (Apache 2.0)
- Transformers: Hugging Face (Apache 2.0)
- UIAutomation: Microsoft Windows SDK
