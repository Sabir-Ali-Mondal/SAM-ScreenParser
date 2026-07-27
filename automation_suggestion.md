# Automation Suggestion

This file is for whoever builds the agent on top of SAM ScreenParser.
SAM itself only looks at the screen and reports what it sees.
It does not decide what to click. The model decides. The clicker clicks.
Keeping these three jobs separate is what makes the whole thing safe.

## Parser First

For a desktop agent, SAM should be the eyes by default.
Bring in a vision model only for things that are not made of text and buttons.

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

## Two Lists, One Id

SAM reads the screen once and writes two lists that share the same id numbers.

```text
        SAM ScreenParser
              |
     one pass over the screen
              |
     two lists, same id numbers
        /            \
       v              v
  List for the     List for the
  model            clicker
  (names +         (the pixel
   types)           spots)
       |              |
       v              v
  Model picks      Clicker finds
  an id            that id and
                   clicks it
```

- The model's list has, for each thing on screen: an `id`, the `text`, the OS `control_type`, and a `type` only when SAM is sure. It has no pixel numbers and no confidence score.
- The clicker's list has the pixel spot (`center`, `bounds`) for each `id`. The model never sees this list.

Because the model never sees pixels, it cannot make up a coordinate.
Because the clicker only clicks ids it was handed, a wrong id clicks nothing.
That is the whole safety idea, in one line each.

## What the Model Sees

```json
{ "id": 12, "text": "Explorer", "type": "sidebar_item", "control_type": "PaneControl" }
{ "id": 18, "text": "Folder",                                "control_type": "PaneControl" }
```

- When `type` is there, SAM matched it for sure, from the OS or from the UI word list. Trust it.
- When `type` is missing, SAM is not sure. The list carries one note at the top, `_guide`, that says so: no type means the parser could not name it, and it is probably just plain text. The model may figure it out from the words around it, or it may leave it alone.

The model also gets the window title, the app kind (IDE, browser, file explorer, desktop), a few yes/no flags (is a dialog open, is it loading), and which element the mouse is resting on. That is all the context it needs. There is no big block of screen text, because every word on screen is already its own line in the list. There is also no confidence number: SAM reports facts, and the model judges for itself.

## How the Model Acts

The model never sends a pixel. It sends an id, and the clicker does the rest.

```json
{ "target_id": 12 }                            // click "Explorer"
{ "target_id": 30, "input": "hello" }          // click a box, then type
{ "target_id": 1,  "action": "double_click" }  // open a desktop icon
```

- No `action` and a known `type`? The clicker picks the obvious verb from the type (a menu or sidebar item gets clicked, an input gets clicked-then-typed).
- No `action` and no `type`? The clicker cannot safely guess a verb, so it refuses. If the model wants to act on an untyped element, it must say the verb itself.
- An `action` is given? The clicker checks it makes sense and refuses if it does not.
- The id is not in the list? The clicker does nothing. A bad id can never hit the wrong place.

## Desktop Icons Need a Double Click

This is the one place to be careful. On the Windows desktop, an icon (Recycle Bin, an app shortcut) reports itself to SAM as a list item, the same as a row inside an app. So SAM labels it `sidebar_item` and cannot tell them apart on its own.

The model tells them apart by where the thing is:

- Sitting on the wallpaper, outside any app window (app kind is desktop) -> it is an icon -> send `"action": "double_click"`.
- A row inside an app's list or sidebar -> it is a normal item -> a single click.

## Use SAM For

- Buttons, text boxes, menus, tabs, dialogs
- Browser UI, File Explorer, Office apps
- IDEs and the terminal
- Desktop icons (with the double-click rule above)
- Reading the text on screen
- Finding where to click
- Driving the mouse and keyboard

## Use a Vision Model For

- Photos, videos, charts, diagrams, maps
- Games, canvas and WebGL, image editors
- Logos, colours, CAPTCHAs
- Judging how something looks (layout, alignment, design)

## Simple Rules for the Agent

1. Give the model only its list. Keep the pixel list for the clicker.
2. The model may only name ids that are in its list.
3. After every click, take a new picture. Ids change every picture, so always use the ids from the newest one. Never use an old id on a new picture.
4. If `type` is missing, treat the thing as plain text unless the words around it clearly say otherwise. If in doubt, skip it.
5. Always click the centre the clicker gives back, and never outside the screen edges.
6. The mouse position is a snapshot. If the mouse might have moved, ask again before trusting it.
7. After each action, check that the screen changed the way you expected. If nothing changed, the click missed; try once more, then stop.
8. A dialog or pop-up comes first. If something is loading, wait. Never click through an overlay.
9. To remember the same button as last time across pictures, match it by window plus type plus text in the new list. Only fall back to a saved spot if it is gone from the new picture, and only once.

## Prompt Template

```text
You are controlling a desktop through a perception engine that reports only
verified facts. You receive a semantic table. Each element has:
  id           - unique within this capture
  text         - OCR-detected text (may contain errors)
  type         - present only when deterministically identified
  control_type - OS accessibility type (often uninformative on Electron apps)

{_guide}

Rules:
1. Trust 'type' when present.
2. If 'type' is absent, treat the element as static text unless the
   surrounding elements and window context strongly indicate otherwise.
   If unsure, do not act on it. If you do act on it, state the verb yourself.
3. Never invent coordinates and never invent ids.
4. To act, emit {"target_id": <id>}. To type, add "input". To override the
   default verb (for example to double-click a desktop icon), add "action".
5. A desktop icon (a list item outside any application window) needs
   "action": "double_click". A list or sidebar entry needs a single click.
6. Use active_window_title, app_type, and screen_state for context.

Active window: {active_window_title}
App type: {app_type}
Screen state: {screen_state}
Cursor over element: {cursor.over_element_id}

Elements:
{elements}

Goal: {user_goal}

Respond with the next plan step, or "don't know" if no element can be
acted upon safely.
```

## Worked Examples

Goal: open the Explorer panel.
The list contains `{"id": 12, "text": "Explorer", "type": "sidebar_item", "control_type": "PaneControl"}`. The type is present and the text matches the goal, so the model emits `{"target_id": 12}`. The clicker resolves id 12 in the pixel list of this capture and clicks its centre. The agent re-captures and confirms the panel is focused.

Goal: open the Recycle Bin on the desktop.
The list contains `{"id": 1, "text": "Recycle Bin", "type": "sidebar_item", "control_type": "ListItemControl"}` with the app kind indicating the desktop. The disambiguation rule applies: a list item outside any application window is an icon. The model emits `{"target_id": 1, "action": "double_click"}`. The clicker double-clicks the resolved centre.

Goal: act on the text `Folder` in the file tree.
The list contains `{"id": 18, "text": "Folder", "control_type": "PaneControl"}` with no `type`. The model infers from context that this is a folder node in the explorer tree and emits `{"target_id": 18}` with the verb it chooses. If the model is not confident, it skips the element rather than guess.

## Routing Rule

> Parser first. Vision only when you must.

The parser handles most desktop tasks on its own.
Save the vision model for the jobs that truly need to see.

This keeps token use low, skips slow vision calls, makes results repeatable,
and keeps the automation honest by using real screen structure whenever it can.

## Why This Separation Matters

The parser is a perception engine, not a classifier. It detects text, locates it, exposes OS facts, and leaves unidentified elements honestly unidentified. The model is the reasoner: it understands what "Save", "Explorer", and "Terminal" mean from context far better than a keyword list, and it is the only component allowed to infer a role for an untyped element. The clicker is the only component that touches pixels, and it does so through an id indirection that turns every bad reference into a refused action. Keeping these three responsibilities separate is what makes the system safe to drive a real machine with.
