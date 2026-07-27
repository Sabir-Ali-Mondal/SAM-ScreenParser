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

SAM ScreenParser is a local, CPU-only desktop perception engine for AI automation agents. It converts a live screen capture into two structured JSON tables: one for the planning model (names and types, no pixels) and one for the executor (pixels resolved by id). The parser reports only verified facts and never guesses a semantic label.

It runs entirely offline on standard laptops with no GPU and no cloud dependency.

---

## Architecture

```text
Desktop Screenshot (DPI-aware)
        |
        v
RapidOCR Sweep + Windows UIA
        |
        v
UI Dataset Matcher (RapidFuzz)
        |
        v
Two-Table Output
 +-- Semantic Table   -> Planning Model (id, text, type?, control_type, _guide)
 +-- Coordinate Table -> Executor (id, bounds, center)
        |
        v
Controller Memory (cross-frame identity)
        |
        v
Desktop Automation Agent
```

The planning model never receives pixel coordinates. It selects an element by **id**; the executor resolves that id into the correct screen position from the matching coordinate table of the same snapshot.

---

## Parser First

For AI desktop automation, **SAM should be the eyes by default**. Bring in a vision model only for things that are not made of text and buttons.

```text
              User request
                    |
                    v
           Run SAM ScreenParser
                    |
          Can the parser see it?
              /            \
            Yes             No
             |               |
        Use the parser   Take a screenshot
             |           and ask a vision model
             \             /
                    v
             Do the action
```

### Use SAM For

- Buttons, text boxes, menus, tabs, dialogs
- Browser UI, File Explorer, Office apps
- IDEs and terminals
- Desktop icons (with double-click disambiguation)
- Reading UI text and finding where to click
- Driving mouse and keyboard via id resolution

### Use a Vision Model For

- Photos, videos, charts, diagrams, maps
- Games, Canvas/WebGL, image editors
- Logos, colours, CAPTCHAs
- Judging how something looks (layout, alignment, design)

---

## Key Design Choices

- **Facts only:** No confidence scores, no actionability filter, no guessed types. Every detected region is passed through; the model decides what is interactive.
- **Type omission:** When the parser cannot identify an element, the `type` field is omitted from the semantic table rather than set to `"unknown"`. This saves tokens and signals honest uncertainty.
- **No screen_text dump:** Every visible text region is already an element, so a separate full-screen text block would be redundant.
- **PaneControl stripped:** On Electron apps where UIA returns `PaneControl` everywhere, the semantic table omits that field so the model's context stays clean.
- **Verb legend stated once:** The mapping from type to allowed actions is embedded as a single `_guide` string, not repeated per element.
- **OpenCV for drawing only:** OpenCV is installed only to produce the verification image. It is not used for detection.

---

## Example Output

```jsonc
// Semantic Table (model input -- no coordinates, no confidence, no screen_text)
{
  "_guide": "If an element has no 'type' field, the parser could not deterministically identify its role...",
  "active_window_title": "Settings - SAM-ScreenParser - Trae",
  "elements": [
    { "id": 3, "text": "File", "type": "menu" },
    { "id": 18, "text": "Folder" }
  ]
}

// Coordinate Table (executor -- never sent to the model)
{
  "metadata": { "image_size": [1920, 1080] },
  "elements": [
    { "id": 3, "bounds": [118, 12, 142, 31], "center": [130, 21] },
    { "id": 18, "bounds": [63, 103, 130, 123], "center": [96, 113] }
  ]
}
```

The model emits `{"target_id": 3}`; the executor looks up id 3 in the coordinate table and clicks `[130, 21]`. Id 18 has no `type`, so the model must infer its role or skip it.

---

## Performance

| Hardware       | Measured Performance             |
| -------------- | -------------------------------- |
| CPU Only       | ~7-13 s per 1920x1080 screen     |
| GPU (Optional) | <1 s via ONNX Runtime CUDA EP    |

*Measured on AMD Ryzen 7 U, 16 GB RAM, Windows 11, Trae IDE.*

---

## Comparison

| Tool                 | Coordinates      | GPU   | Offline | Speed     |
| -------------------- | ---------------- | ----- | ------- | --------- |
| **SAM ScreenParser** | Exact            | No    | Yes     | 7-13 s    |
| OmniParser v2        | Exact            | Yes   | Yes     | 1-3 s     |
| UI-TARS-7B           | Approximate      | Yes   | Yes     | 5-10 s    |
| GPT-4o Vision        | Approximate      | Cloud | No      | 3-5 s     |
| Pure UIA             | Native apps only | No    | Yes     | <1 s      |

---

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install rapidocr_onnxruntime opencv-python pillow numpy uiautomation rapidfuzz

# Verify installation
py -c "from rapidocr_onnxruntime import RapidOCR; from rapidfuzz import fuzz; print('OK')"

# Run unified test: captures screen, draws detections, writes both JSON tables
py test_screen.py
```

RapidOCR downloads its ONNX models (~80 MB) automatically on first use. No Tesseract, PyTorch, or Transformers required.

---

## Documentation

This README covers the overview and quick start. For complete details:

- **[technical_documentation.md](technical_documentation.md)** -- Engine architecture, output schema, parser guarantees, accuracy analysis, known limitations, setup and maintenance.
- **[automation_suggestion.md](automation_suggestion.md)** -- Agent loop diagram, prompt template, simple rules, desktop-icon double-click rule, cross-frame memory, worked examples, routing guidance.

---

## License

- PaddleOCR / RapidOCR -- Apache 2.0
- ONNX Runtime -- MIT
- OpenCV -- Apache 2.0
- RapidFuzz -- MIT
- Windows UI Automation -- Microsoft

---

## Vision

SAM ScreenParser is a **parser-first perception layer** for desktop AI agents.

It provides deterministic UI understanding with pixel-perfect coordinates while leaving true visual reasoning -- photographs, charts, games, graphics, and image analysis -- to dedicated vision models. The two-table interface ensures the model can never hallucinate a coordinate, and the fact-only design ensures the parser never lies about what it sees.
