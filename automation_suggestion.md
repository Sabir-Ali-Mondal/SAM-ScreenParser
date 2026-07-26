## AI Routing Strategy

```text
                USER REQUEST
                      │
                      ▼
      Generate Semantic + Coordinate Tables
                      │
                      ▼
 Can the Semantic Table satisfy the request?
                      │
            ┌─────────┴─────────┐
            │                   │
           YES                 NO
            │                   │
            ▼                   ▼
     Use Parser Only     Capture Screenshot
            │                   │
            │             Vision Model
            │                   │
            └─────────┬─────────┘
                      ▼
             LLM Creates Plan
                      │
                      ▼
       Executor Resolves ID → Coordinates
                      │
                      ▼
               Execute Action
```

### Parser (Default)

Use the parser for:

* Buttons
* Textboxes
* Menus
* Tabs
* Lists
* Dialogs
* Windows
* Browser UI
* File Explorer
* IDEs
* Terminal
* Office apps
* Desktop icons
* Taskbar
* Reading UI text
* Finding elements
* All automation actions

The planning LLM receives only the **Semantic Table** (IDs, text, type, action, confidence). It never receives coordinates.

### Vision (Fallback)

Use a screenshot + vision model only for:

* Photos
* Videos
* Charts
* Diagrams
* Maps
* Logos
* Colors
* Shapes
* Icons without labels
* CAPTCHA
* Canvas/WebGL
* Games
* Visual appearance or layout

### Hybrid Mode

Use **Parser + Vision** when both UI interaction and visual understanding are required (e.g., interacting with charts, images, or graphics).

### Routing Rule

```text
Parser = Default (~95% of requests)

Vision = Fallback only when structured UI cannot represent the required information.

LLM → Element ID
Executor → ID → Coordinates → Action
```
