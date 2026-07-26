# Automation Suggestion

## Parser-First Architecture

For an AI desktop agent, **SAM ScreenParser should be the default perception layer**. Use vision models only when the required information cannot be represented as structured UI.

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

---

## Use SAM ScreenParser For

- Buttons
- Textboxes
- Menus
- Tabs
- Dialogs
- Browser UI
- File Explorer
- IDEs
- Terminal
- Office applications
- Desktop icons
- Reading UI text
- Finding coordinates
- Mouse and keyboard automation

---

## Use Vision Models For

- Photos
- Videos
- Charts
- Diagrams
- Maps
- Games
- Canvas/WebGL
- Logos
- Colors
- CAPTCHA
- Image editing
- Visual appearance (layout, alignment, design quality)

---

## Routing Rule

> **Parser First → Vision Only When Needed**

The parser is sufficient for **most desktop automation tasks**, while vision models should be reserved for tasks requiring true visual understanding.

This approach reduces token usage, avoids unnecessary vision inference, improves reliability, and keeps automation deterministic by using structured UI whenever possible.
