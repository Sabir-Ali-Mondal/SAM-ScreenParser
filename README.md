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

Each detected element includes its exact screen coordinates, semantic type, interaction state, confidence score, and cursor context, allowing an automation controller to interact with the operating system using real coordinates instead of estimated locations.

The entire pipeline runs **fully offline**, requires **no cloud APIs**, and is designed to work on **CPU-only systems**, making it suitable for standard laptops and local AI agents.

Rather than replacing vision models, SAM acts as the primary perception layer for desktop automation. Vision models remain useful for photographs, charts, videos, graphical canvases, and other content that cannot be represented as structured UI data.

---

# Why SAM ScreenParser?

Modern Vision Language Models are excellent at understanding images.

However, desktop automation requires something different:

* Deterministic coordinates
* Reliable UI understanding
* Minimal token usage
* Repeatable execution
* Safe automation

Instead of asking an LLM to rediscover the interface from pixels on every step, SAM extracts structured UI information once and lets the language model reason over that representation.

This dramatically reduces unnecessary visual reasoning while improving automation reliability.

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

# What SAM Produces

Every frame is converted into structured JSON describing the current desktop.

Example:

```json
{
  "id": 20,
  "type": "button",
  "text": "Download",
  "bounds": [10,461,87,479],
  "confidence": 0.98
}
```

Instead of sending screenshots, the LLM reasons over structured UI elements.

---

# What It Guarantees

* Pixel-perfect element coordinates derived from Florence-2 grounding and mapped back to the original screen resolution.
* Clean OCR using Tesseract with preprocessing, contrast normalization, and removal of icon-related text noise.
* DPI-aware coordinate mapping so screenshot coordinates, cursor coordinates, UI Automation coordinates, and click locations remain consistent across display scaling.
* Confidence score for every detected element so controllers can make informed decisions.
* Cursor context identifying the actual operating system control beneath the mouse pointer.
* Structured JSON optimized for desktop automation.

---

# What It Does **Not** Guarantee

SAM intentionally refuses to guess.

If an element cannot be identified with sufficient confidence, it is better to decline the action than click the wrong control.

This is a deliberate safety feature rather than a limitation.

---

# Features

* Pixel-perfect element coordinates
* High-quality OCR extraction
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
* Canvas/WebGL applications
* Logos
* Colors
* Visual aesthetics
* CAPTCHA

SAM is designed to complement vision models rather than replace them.

---

# Comparison

| Traditional Vision Pipeline | SAM ScreenParser              |
| --------------------------- | ----------------------------- |
| Screenshot input            | Structured JSON               |
| Vision reasoning every step | Parser-first reasoning        |
| Estimated coordinates       | Pixel-perfect coordinates     |
| High visual token cost      | Compact structured data       |
| Coordinates may hallucinate | Deterministic coordinates     |
| Requires large VLMs         | Works with small local LLMs   |
| Harder to debug             | Easy to inspect and debug     |
| Slower automation           | Efficient controller pipeline |

---

# Quick Start

```powershell
py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation

py screen_analyzer.py
```

---

# Documentation

The repository documentation contains:

* Internal architecture
* Detection pipeline
* JSON schema
* Controller contract
* Confidence rules
* Safety rules
* Coordinate mapping
* Integration guide

See:

`technical_documentation.md`

---

# License & Credits

This project builds upon the following open-source software:

* Microsoft Research — Florence-2 (Apache 2.0)
* Google — Tesseract OCR (Apache 2.0)
* Hugging Face — Transformers (Apache 2.0)
* OpenCV Project — OpenCV (Apache 2.0)
* Microsoft — Windows UI Automation SDK

---

# Vision

The long-term goal of SAM ScreenParser is to provide a reliable perception layer for local AI desktop agents.

Instead of forcing language models to repeatedly interpret screenshots, SAM exposes the desktop as structured, deterministic data that is easier to reason over, more efficient to process, and safer to automate.

The result is a parser-first architecture where vision is reserved for genuinely visual content, allowing even small local language models to perform reliable desktop automation on ordinary hardware.
