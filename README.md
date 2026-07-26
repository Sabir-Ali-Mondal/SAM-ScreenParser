# SAM ScreenParser

> **Pixel-perfect screen understanding for AI desktop agents.**

> **Note on Naming**
> **SAM** stands for **Screen Automation Manager** and is also a nod to the author's initials, **Sabir Ali Mondal**.
> This project is completely independent and **is NOT related to Meta's Segment Anything Model (SAM).**

---

# Overview

SAM ScreenParser is a local screen understanding engine designed for AI desktop agents.

Instead of repeatedly sending screenshots to a vision-language model, SAM converts the current desktop into compact, structured JSON that language models can reason over efficiently.

The pipeline combines **Florence-2** for pixel-perfect grounding, **Tesseract OCR** for clean text extraction, **Windows UI Automation** for semantic enrichment, and screen-state analysis to produce deterministic, automation-ready output.

Each detected element includes its exact screen coordinates, semantic type, interaction state, confidence score, cursor context, and screen metadata, allowing an automation controller to interact with the operating system using deterministic coordinates instead of estimated locations.

The entire pipeline runs **fully offline**, requires **no cloud APIs**, and is designed to work on **CPU-only systems**, making it suitable for standard laptops and local AI desktop agents.

Rather than replacing vision models, SAM acts as the primary perception layer for desktop automation. Vision models remain useful for photographs, charts, videos, graphical canvases, games, and other content that cannot be represented as structured UI data.

---

# Design Philosophy

Traditional desktop agents repeatedly send screenshots to a vision-language model and ask it to rediscover the interface on every step.

SAM ScreenParser follows a **parser-first architecture**. It converts the desktop into structured, automation-ready JSON, allowing language models to reason over deterministic UI data instead of raw pixels.

Vision models remain a fallback for photographs, charts, graphics, and other purely visual content that cannot be represented as structured UI.

This approach reduces unnecessary visual reasoning, improves reliability, and enables efficient desktop automation with small local language models.

---

# Why SAM ScreenParser?

Modern Vision Language Models are excellent at understanding images.

Desktop automation, however, requires something different:

* Deterministic coordinates
* Reliable UI understanding
* Minimal visual reasoning
* Repeatable execution
* Safe controller behavior

Instead of asking an LLM to rediscover the interface from pixels every time, SAM extracts structured UI information once and allows the language model to reason over that representation.

---

# Architecture

```text
                     Desktop Screen
                           │
                           ▼
                  SAM ScreenParser
                           │
       ┌───────────────────┼────────────────────┐
       │                   │                    │
       ▼                   ▼                    ▼
 Florence-2          Tesseract OCR      Windows UIA
 Pixel Grounding      Text Extraction   Semantic Data
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │
                           ▼
                  Screen State Analysis
                           │
                           ▼
                 Cursor Context Detection
                           │
                           ▼
                Structured Automation JSON
                           │
                           ▼
                     Planning LLM
                           │
                           ▼
                 Desktop Automation Agent
```

---

# Example Output

```json
{
  "cursor": {
    "position": [183, 306],
    "control_type": "TreeItem",
    "over_element_id": 26
  },
  "screen_state": {
    "active_app_type": "file_explorer",
    "has_dialog": false
  },
  "elements": [
    {
      "id": 20,
      "type": "button",
      "text": "Download",
      "action": "click",
      "bounds": [10, 461, 87, 479],
      "center": [48, 470],
      "confidence": 0.98
    }
  ]
}
```

---

# What It Guarantees

* Pixel-perfect element coordinates derived from Florence-2 grounding and mapped back to the original screen resolution.
* Clean OCR using Tesseract with preprocessing, contrast normalization, and icon-noise removal.
* DPI-aware coordinate mapping so screenshot coordinates, UI Automation coordinates, cursor coordinates, and click locations remain consistent across display scaling.
* Confidence score for every detected element.
* Cursor context identifying the real operating system control beneath the mouse pointer.
* Structured JSON optimized for LLM desktop automation.
* Fully local execution with no cloud dependency.

---

# What It Does **Not** Guarantee

SAM intentionally refuses to guess.

If an element cannot be identified with sufficient confidence, it is better to decline the action than click the wrong control.

This is a deliberate safety feature rather than a limitation.

> **Controller Contract**
>
> Any automation agent consuming this output **must** enforce the controller contract defined in `technical_documentation.md`. Controllers should only execute actions on elements that satisfy the configured confidence threshold and validation rules.

---

# Features

* Pixel-perfect element coordinates
* Florence-2 visual grounding
* High-quality OCR extraction
* Windows UI Automation enrichment
* Structured UI elements
* Confidence-gated detections
* Cursor context
* Screen state detection
* Automation-ready JSON
* DPI-aware coordinate mapping
* CPU-friendly execution
* Fully offline
* No cloud APIs required
* Optimized for LLM desktop agents

---

# When To Use SAM

SAM should be the **default perception layer** for desktop automation.

Ideal for:

* Buttons
* Textboxes
* Menus
* Dropdowns
* Tabs
* Dialogs
* Browser automation
* Windows applications
* File Explorer
* Visual Studio Code
* Office applications
* Terminal
* Desktop icons
* Taskbar
* Context menus
* Reading UI text
* Precise mouse interaction

---

# When Vision Models Are Still Needed

Vision models remain valuable for information that cannot be represented as structured UI.

Examples include:

* Photographs
* Videos
* Charts
* Graphs
* Diagrams
* Maps
* Image editing
* Game scenes
* Canvas / WebGL applications
* Logos
* Colors
* Visual aesthetics
* CAPTCHA

SAM is designed to complement vision models rather than replace them.

---

# Comparison

| Capability | Traditional UI Parser (UIA / Accessibility APIs) | Vision Language Models | SAM ScreenParser |
|------------|--------------------------------------------------|------------------------|------------------|
| Standard UI Detection | Excellent | Good | Excellent |
| Custom / Canvas UI Detection | Poor | Excellent | Excellent |
| OCR Text Extraction | No | Yes | Yes |
| Pixel-perfect Coordinates | Limited | Approximate | Yes |
| Click Coordinates | API-dependent | Estimated | Deterministic |
| Works on Any Application | No | Yes | Yes |
| Browser Support | Partial | Yes | Yes |
| Desktop Support | Partial | Yes | Yes |
| Games | Poor | Good | Good |
| Canvas / WebGL | No | Yes | Yes |
| Image Understanding | No | Excellent | Via Vision Fallback |
| Graph / Chart Understanding | No | Excellent | Via Vision Fallback |
| UI Semantics | Excellent | Medium | Excellent |
| Coordinate Hallucination | None | Possible | None |
| OCR Accuracy | None | Medium | High |
| Controller-ready Output | Partial | No | Yes |
| Structured JSON Output | Limited | No | Yes |
| Confidence Scores | Rare | Limited | Yes |
| Cursor Context | No | No | Yes |
| Screen State Detection | No | Limited | Yes |
| DPI-aware Coordinates | API-dependent | No | Yes |
| Automation Safety | Medium | Low | High |
| Token Usage | Very Low | Very High | Low |
| CPU Usage | Very Low | High | Medium |
| GPU Required | No | Usually | No |
| Cloud Required | No | Often | No |
| Offline Execution | Yes | Sometimes | Yes |
| Deterministic Output | Yes | No | Yes |
| Easy Debugging | Medium | Difficult | Excellent |
| Small LLM Friendly | N/A | Poor | Excellent |
| Local AI Friendly | Excellent | Limited | Excellent |
| Multi-monitor Support | Limited | Yes | Yes |
| Production Automation | Good | Poor | Excellent |
| Designed for AI Agents | No | General Purpose | Yes |

---

# Quick Start

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation

# Verify Tesseract installation
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

py screen_analyzer.py
```

---

# Documentation

Detailed documentation includes:

* System architecture
* Processing pipeline
* Detection flow
* JSON schema
* Controller contract
* Confidence rules
* Coordinate mapping
* DPI handling
* Integration guide
* Safety rules
* Performance notes

See:

```text
technical_documentation.md
```

---

# License & Credits

This project builds upon the following open-source software:

* Microsoft Research — Florence-2 (Apache 2.0)
* Google — Tesseract OCR (Apache 2.0)
* Hugging Face — Transformers (Apache 2.0)
* OpenCV Project — OpenCV (Apache 2.0)
* Microsoft — Windows UI Automation SDK

Please refer to each project's respective license for complete terms.

---

# Vision

The long-term goal of SAM ScreenParser is to provide a reliable perception layer for local AI desktop agents.

Instead of forcing language models to repeatedly interpret screenshots, SAM exposes the desktop as structured, deterministic data that is easier to reason over, more efficient to process, and safer to automate.

The result is a **parser-first architecture**, where structured UI understanding is the default and vision models are reserved only for genuinely visual tasks. This enables reliable desktop automation even with small local language models running on ordinary hardware.
