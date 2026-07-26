# SAM ScreenParser

**Note on Naming:** In this project, **SAM** stands for **S**creen **A**utomation **M**anager (and is also a nod to the author's initials, **S**abir **A**li **M**ondal).
*This project is entirely independent and is NOT related to Meta's Segment Anything Model (SAM).*

## Project Overview

SAM ScreenParser is a local, CPU-friendly screen understanding pipeline for desktop automation agents. It converts live screenshots into structured, deterministic JSON containing pixel-perfect coordinates, clean text, element classifications, window context, and a per-element confidence score. It runs entirely offline on standard laptops with no cloud APIs and no dedicated GPU.

What it guarantees:

- Pixel-perfect coordinates from Florence-2 vision grounding, mapped to the image's true pixel size, so detection is resolution-independent.
- Clean text from Tesseract OCR with contrast normalization and icon-garbage removal.
- DPI-aware capture so detection coordinates, UIA coordinates, and click coordinates agree on scaled displays.
- A confidence score on every element so a controller can refuse to act on uncertain data.

What it does not guarantee, by design: it will decline to act on elements it cannot classify with confidence rather than click the wrong target. That refusal is a feature, not a gap.

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

