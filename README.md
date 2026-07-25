# SAM-ScreenParser
An LLM-powered vision engine that converts screenshots into structured, deterministic screen representations for AI desktop automation and reasoning.

Project: SAM ScreenParser

Goal
-------------------------------------------------------------------------------
This project aims to convert a screenshot into a complete, compact, structured,
and deterministic screen representation that another AI agent can understand
and use for desktop automation.

Instead of asking an LLM to directly click or reason from raw images every time,
the vision model acts as a "Screen Parser".

The parser should:
- Understand the complete screen.
- Detect every visible object.
- Preserve visual hierarchy.
- Extract all readable text.
- Describe interaction state.
- Provide approximate coordinates.
- Never hallucinate hidden content.
- Never intentionally ignore visible objects.
- Produce consistent output for the same screenshot.

The output will later be parsed by another automation agent capable of:
- Mouse movement, Clicking, Double-clicking, Drag & Drop
- Keyboard typing, Scrolling
- Screen comparison, UI state tracking, Task planning

Long-term Goal
-------------------------------------------------------------------------------
Screenshot -> Vision LLM (ScreenParser) -> Structured Screen Description
         -> Planning LLM -> Python Desktop Automation Agent
===============================================================================
