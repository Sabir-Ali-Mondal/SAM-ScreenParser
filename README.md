# SAM ScreenParser

> **Pixel-perfect screen understanding for AI desktop agents.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Offline](https://img.shields.io/badge/Offline-Yes-green)
![GPU](https://img.shields.io/badge/GPU-Not_Required-orange)
![License](https://img.shields.io/badge/License-Apache_2.0-brightgreen)

> **SAM** stands for **Screen Automation Manager** (and the author's initials, **S**abir **A**li **M**ondal). This project is **not related to Meta's Segment Anything Model**.

---

# Overview

SAM ScreenParser is a lightweight **desktop perception engine** for AI automation.

Instead of sending screenshots to vision models every step, SAM converts the desktop into structured JSON containing:

* Interactive UI elements
* Pixel-perfect coordinates
* Full-screen visible text
* Active window information
* Screen state
* Cursor context
* Confidence scores

It runs **fully offline**, requires **no GPU**, and is designed for **small local LLMs**.

---

# Architecture

```text
Desktop Screen
      │
      ▼
SAM ScreenParser
      ├── RapidOCR (OCR)
      ├── Windows UI Automation
      ├── Screen State Analysis
      ▼
Two Outputs
 ├── Semantic Table → Planning LLM
 └── Coordinate Table → Executor
      ▼
Controller Memory
      ▼
Desktop Automation Agent
```

The planning LLM never receives pixel coordinates. It selects an element by **id**, while the executor resolves that id into the correct screen position from the matching coordinate table.

---

# Parser-First Architecture

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

* Buttons
* Textboxes
* Menus
* Tabs
* Dialogs
* Browser UI
* File Explorer
* IDEs
* Terminal
* Office applications
* Desktop icons
* Reading UI text
* Finding coordinates
* Mouse and keyboard automation

### Use Vision Models For

* Photos
* Videos
* Charts
* Diagrams
* Maps
* Games
* Canvas/WebGL
* Logos
* Colors
* CAPTCHA
* Image editing
* Visual appearance and layout evaluation

---

# Features

* Fully offline
* CPU-friendly
* No GPU required
* No cloud APIs
* Pixel-perfect coordinates
* Full-screen text extraction
* Windows UI Automation enrichment
* Confidence-based detection
* Two-table architecture for safe automation
* Controller memory for cross-frame identity
* Optimized for local LLMs

---

# Example Output

```json
// Semantic Table (LLM receives this)
{
  "id": 12,
  "text": "Save",
  "type": "button",
  "confidence": 0.90
}

// Coordinate Table (Executor resolves id 12 from this)
{
  "id": 12,
  "center": [850, 430],
  "bounds": [820, 415, 880, 445]
}
```

The LLM plans using the semantic table, while the executor resolves the same **id** to exact screen coordinates from the coordinate table.

---

# Performance

| Hardware       | Performance                  |
| -------------- | ---------------------------- |
| CPU Only       | ~6–8 s per 1920×1080 screen  |
| GPU (Optional) | Faster via ONNX Runtime CUDA |

---

# Comparison

| Tool                 | Coordinates      | GPU   | Offline |
| -------------------- | ---------------- | ----- | ------- |
| **SAM ScreenParser** | Exact            | No    | Yes     |
| OmniParser           | Exact            | Yes   | Yes     |
| UI-TARS              | Approximate      | Yes   | Yes     |
| GPT-4o Vision        | Approximate      | Cloud | No      |
| Pure UIA             | Native apps only | No    | Yes     |

---

# Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation

# Verify installation
py -c "from rapidocr_onnxruntime import RapidOCR; print('OK')"

py screen_analyzer.py
```

RapidOCR automatically downloads its ONNX models on first use.

---

# Documentation

For complete implementation details, see **technical_documentation.md**, including:

* System architecture
* Two-table interface
* Controller contract
* Controller memory
* Verb legend
* Integration guide
* Setup and maintenance
* Accuracy analysis
* Known limitations

---

# License

* RapidOCR / PaddleOCR — Apache 2.0
* ONNX Runtime — MIT
* OpenCV — Apache 2.0
* Windows UI Automation — Microsoft

---

# Vision

SAM ScreenParser is a **parser-first perception layer** for desktop AI agents.

It provides deterministic UI understanding with pixel-perfect coordinates while leaving true visual reasoning—such as photographs, charts, games, graphics, and image analysis—to dedicated vision models.

This version keeps the README concise while clearly explaining the project's purpose, parser-first workflow, architecture, quick start, and where to find the full technical documentation. The implementation details remain in `technical_documentation.md`, avoiding duplication while still making the README self-contained.
