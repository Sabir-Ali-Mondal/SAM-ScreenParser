# SAM ScreenParser

> **Pixel-perfect screen understanding for AI desktop agents.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Offline](https://img.shields.io/badge/Offline-Yes-green)
![GPU](https://img.shields.io/badge/GPU-Not_Required-orange)
![License](https://img.shields.io/badge/License-Apache_2.0-brightgreen)

> **SAM** stands for **Screen Automation Manager** (and the author's initials, **S**abir **A**li **M**ondal).  
> This project is **not related to Meta's Segment Anything Model**.

---

## Overview

SAM ScreenParser is a lightweight **desktop perception engine** for AI automation.

Instead of sending screenshots to vision models every step, SAM converts the desktop into structured JSON containing:

-   Interactive UI elements with pixel-perfect coordinates
-   Full-screen visible text summary
-   Active window information and screen state
-   Cursor context (what is under the pointer)
-   Confidence scores on every element

It runs **fully offline**, requires **no GPU**, and is designed for **small local LLMs**.

---

## Architecture

```text
Desktop Screen
      │
      ▼
SAM ScreenParser
      ├── RapidOCR / PaddleOCR (detection + text)
      ├── Windows UI Automation (semantics + cursor)
      └── Screen State Analysis
            ▼
Two Outputs
 ├── Semantic Table  → Planning LLM (no coordinates)
 └── Coordinate Table → Executor (pixels resolved by id)
            ▼
Controller Memory (cross-frame identity)
            ▼
Desktop Automation Agent
```

The planning LLM never receives pixel coordinates. It selects an element by **id**; the executor resolves that id into the correct screen position from the matching coordinate table of the same snapshot.

---

## Parser-First Architecture

For AI desktop automation, **SAM ScreenParser should be the default perception layer**. Use vision models only when the required information cannot be represented as structured UI.

```text
              User Request
                    │
                    ▼
        Generate SAM ScreenParser Data
                    │
                    ▼
     Can the parser answer the request?
            │                 │
           Yes               No
            │                 │
            ▼                 ▼
      Use Parser      Capture Screenshot
            │                 │
            │          Vision Model
            │                 │
            └─────────┬───────┘
                      ▼
              Execute Action
```

### Use SAM ScreenParser For

-   Buttons, textboxes, menus, tabs, dialogs
-   Browser UI, File Explorer, Office applications
-   IDEs and terminals (with Electron-aware classification)
-   Reading UI text and finding click coordinates
-   Mouse and keyboard automation via id resolution

### Use Vision Models For

-   Photos, videos, charts, diagrams, maps
-   Games, Canvas/WebGL, image editing
-   Logos, colors, CAPTCHA
-   Visual appearance and layout evaluation

---

## Features

-   Fully offline, CPU-friendly, no cloud APIs
-   Pixel-perfect coordinates via RapidOCR detector
-   Two-table architecture: LLM reasons over names/ids, executor owns pixels
-   Verb legend stated once (not per element) for minimal token usage
-   Controller memory for safe cross-frame identity tracking
-   Electron/Chromium-aware classification (text-keyword fallback when UIA collapses)
-   Confidence-gated detections with explicit controller contract
-   Unified test script (`test_screen.py`) for instant visual verification

---

## Example Output

```jsonc
// Semantic Table (LLM receives this — NO coordinates, NO per-element verb)
{ "id": 12, "text": "Save", "type": "button", "confidence": 0.90 }

// Coordinate Table (Executor resolves id 12 from this)
{ "id": 12, "center": [850, 430], "bounds": [820, 415, 880, 445], "action": "click" }
```

The LLM emits `{"target_id": 12}`; the executor looks up id 12 in the coordinate table and clicks `[850, 430]`. A hallucinated or stale id returns nothing and is safely refused.

---

## Performance

| Hardware       | Measured Performance             |
| -------------- | -------------------------------- |
| CPU Only       | ~13–15 s per 1920×1080 screen    |
| GPU (Optional) | <1 s via ONNX Runtime CUDA EP    |

*Measured on AMD Ryzen 7 U, 16 GB RAM, Windows 11, Trae IDE (Electron).*

---

## Comparison

| Tool                 | Coordinates      | GPU   | Offline | Speed     |
| -------------------- | ---------------- | ----- | ------- | --------- |
| **SAM ScreenParser** | Exact            | No    | Yes     | 13–15 s   |
| OmniParser v2        | Exact            | Yes   | Yes     | 1–3 s     |
| UI-TARS-7B           | Approximate      | Yes   | Yes     | 5–10 s    |
| GPT-4o Vision        | Approximate      | Cloud | No      | 3–5 s     |
| Pure UIA             | Native apps only | No    | Yes     | <1 s      |

---

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation

# Verify installation
py -c "from rapidocr_onnxruntime import RapidOCR; print('OK')"

# Run unified test: captures screen, draws all detections, writes both JSON tables
py test_screen.py
```

RapidOCR automatically downloads its ONNX models (~80 MB) on first use. No Tesseract, PyTorch, or Transformers required.

---

## Documentation

For complete implementation details, see **[technical_documentation.md](technical_documentation.md)**:

-   System architecture and two-table interface design
-   Controller contract (16 rules for safe execution)
-   Controller memory for cross-frame identity
-   Verb legend and validated plan-step schema
-   Electron/Chromium classification guard
-   Setup, version maintenance, and environment recovery
-   Accuracy analysis and known limitations

---

## License

-   RapidOCR / PaddleOCR — Apache 2.0
-   ONNX Runtime — MIT
-   OpenCV — Apache 2.0
-   Windows UI Automation — Microsoft

---

## Vision

SAM ScreenParser is a **parser-first perception layer** for desktop AI agents.

It provides deterministic UI understanding with pixel-perfect coordinates while leaving true visual reasoning — photographs, charts, games, graphics, and image analysis — to dedicated vision models. The two-table interface ensures the LLM can never hallucinate a coordinate, and the controller contract ensures the executor never acts on uncertainty.
