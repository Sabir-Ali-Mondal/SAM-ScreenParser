# SAM ScreenParser

> **Pixel-perfect screen understanding for AI desktop agents.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-Apache_2.0-green)
![GPU](https://img.shields.io/badge/GPU-Not_Required-orange)
![Offline](https://img.shields.io/badge/Cloud-Not_Required-yellow)

> **Note on Naming:** **SAM** stands for **Screen Automation Manager** (and the author's initials, **S**abir **A**li **M**ondal). This project is independent and **NOT related to Meta's Segment Anything Model.**

---

# Overview

SAM ScreenParser converts the live desktop into compact, structured JSON for AI agents. Instead of sending screenshots to vision models, it provides deterministic coordinates, full-screen text context, and semantic UI data that LLMs can reason over efficiently.

The pipeline combines **Florence-2** for pixel-perfect grounding, **dual-layer Tesseract OCR** for element text + full-screen context, and **Windows UI Automation** for semantic enrichment. It runs **fully offline** on CPU-only systems with no cloud APIs.

SAM is a perception layer, not a vision model replacement. Vision models remain necessary for photographs, charts, games, and canvas content.

---

# Architecture

```text
Desktop Screen → SAM ScreenParser
    ├── Florence-2 (pixel grounding)
    ├── Dual-Layer OCR (element crops + full-screen summary)
    ├── Windows UIA (semantic enrichment + cursor context)
    └── Screen State Analysis
            ↓
    Structured JSON (elements + screen_text + cursor)
            ↓
    Planning LLM → Desktop Automation Agent
```

---

# Example Output

```json
{
  "screen_text": {
    "raw_text": "Explorer screen_analyzer.py\n(.venv) PS D:\\Projects> py screen_analyzer.py\nLive analysis complete in 89.2s",
    "char_count": 1059, "line_count": 26, "is_truncated": false
  },
  "cursor": { "position": [183, 306], "control_type": "TreeItem", "over_element_id": 26 },
  "screen_state": { "active_app_type": "ide", "has_dialog": false },
  "elements": [{
    "id": 20, "type": "button", "text": "Download", "action": "click",
    "bounds": [10, 461, 87, 479], "center": [48, 470], "confidence": 0.98
  }]
}
```

---

# Guarantees & Limitations

**Guarantees:**
- Pixel-perfect coordinates from Florence-2, resolution-independent
- Clean element OCR + full-screen visible text summary (<1s overhead)
- DPI-aware mapping across screenshot, UIA, cursor, and click coordinates
- Confidence scores on every element; cursor OS-level control identification
- Fully local, offline, no cloud dependency

**Does NOT Guarantee:**
SAM refuses to guess. Low-confidence elements are excluded rather than mislabeled. This is a safety feature.

**Known Cons:**
- 45–90s processing on CPU; not real-time
- Small icons, nested elements, and icon-only controls may be missed
- No parent-child hierarchy, Z-order, scroll state, or hidden element detection
- Dense UI regions may have merged lines in full-screen text
- English-only keyword heuristics; non-English relies on control type
- Requires vision model fallback for images, charts, videos, and canvas content

> **Controller Contract:** Agents **must** enforce the contract in `technical_documentation.md`. Only act on elements above confidence threshold (default `0.6`). Use `screen_text` for context, `elements` for interaction.

---

# Features

- Pixel-perfect coordinates via Florence-2
- Dual-layer OCR (element + full-screen summary)
- Windows UIA enrichment + cursor context
- Confidence-gated detections + screen state
- DPI-aware coordinate mapping
- CPU-friendly, fully offline, no cloud APIs
- Optimized for small local LLMs

---

# When To Use SAM vs Vision Models

| Use SAM For | Use Vision Models For |
| :--- | :--- |
| Buttons, inputs, menus, tabs, dialogs | Photographs, videos, charts, diagrams |
| Browser/native app/terminal automation | Game scenes, Canvas/WebGL, image editing |
| Reading UI text, precise mouse interaction | Logos, colors, visual aesthetics, CAPTCHA |
| Providing LLM context without screenshots | Any non-structured visual content |

---

# Comparison of Approaches

| Tool | VRAM | Speed | Coordinates | Semantic UI | Best For |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SAM ScreenParser** | 0 GB (CPU) | 70-90s | Pixel-perfect | Good | CPU laptops, offline, privacy |
| **OmniParser v2** | 8-16 GB GPU | 1-3s | Pixel-perfect | Excellent | GPU workstations, production |
| **UI-TARS-7B** | 12-16 GB GPU | 5-10s | Approximate | Excellent | Complex GUI reasoning |
| **OS-ATLAS-7B** | 12-16 GB GPU | 5-10s | Good | Excellent | GUI automation w/ GPU |
| **Qwen2.5-VL-7B** | 14-16 GB GPU | 10-20s | Approximate | Good | General vision tasks |
| **Moondream2** | 2-4 GB GPU | 10-15s | None | Good | Lightweight semantics |
| **GPT-4o / ScreenAI** | Cloud | 3-5s | Approximate | Excellent | Cloud-first, no local compute |
| **Pure UIA** | 0 GB | <1s | Exact (if avail) | Excellent | Native Windows apps only |

---

# Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install transformers==4.45.0 torch pillow timm einops pytesseract opencv-python uiautomation

# Verify Tesseract
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

py screen_analyzer.py
```

Full documentation (schema, controller contract, DPI handling, integration guide): [`technical_documentation.md`](technical_documentation.md)

---

# License & Credits

- Florence-2: Microsoft Research (Apache 2.0)
- Tesseract OCR: Google (Apache 2.0)
- Transformers: Hugging Face (Apache 2.0)
- OpenCV: OpenCV Team (Apache 2.0)
- UIAutomation: Microsoft Windows SDK

---

# Vision

SAM exposes the desktop as structured, deterministic data with complete visible text context. This **parser-first architecture** enables reliable desktop automation with small local LLMs on ordinary hardware, reserving vision models only for genuinely visual tasks.
