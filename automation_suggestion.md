For a AI router, I'd make the parser the **default**. Only fall back to image analysis when the parser cannot represent the information needed.

```text
                    USER REQUEST
                         │
                         ▼
            Get Structured UI Parser Data
                         │
                         ▼
        Can the parser satisfy the request?
                         │
              ┌──────────┴──────────┐
              │                     │
            YES                    NO
              │                     │
              ▼                     ▼
      Use Parser Only       Is visual understanding required?
              │                     │
              │            ┌────────┴────────┐
              │            │                 │
              │           YES               NO
              │            │                 │
              ▼            ▼                 ▼
      LLM + Parser   Capture Screenshot   Use Parser
                         │
                         ▼
                  Vision Model
                         │
                         ▼
              Combine Vision + Parser
                         │
                         ▼
                    Execute Action
```

### Treat the parser as the primary source

**Always use the parser for:**

* Buttons
* Textboxes
* Menus
* Tabs
* Lists
* Tree views
* Dialogs
* Windows
* Browser UI
* File Explorer
* IDEs (VS Code, Visual Studio, etc.)
* Terminal
* Office applications
* Desktop icons
* Taskbar
* Context menus
* Any clickable UI element
* Reading UI text
* Finding coordinates
* Automation actions

### Use image understanding only for true visual content

Use a screenshot + vision model only when the task depends on information the parser cannot encode, such as:

* Photos
* Videos
* Charts and graphs
* Diagrams
* Maps
* Icons without labels
* Colors ("click the blue button")
* Shapes
* Logos
* CAPTCHA
* Canvas/WebGL content
* Games
* Image editing
* Visual appearance ("does this look centered?" or "is this design good?")

### Rule for your router

```text
Parser = Default (≈95% of requests)

Image = Fallback only for graphics and visual semantics that cannot be represented as structured UI.
```

This is the architecture I'd recommend for your agent because it minimizes token usage, avoids unnecessary vision inference, and relies on the parser whenever it already has the information needed for reliable automation.
