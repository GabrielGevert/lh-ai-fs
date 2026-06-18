"""Named agents of the BS Detector pipeline.

Each module defines one agent with an explicit NAME, an explicit prompt, and a
single run function. Agents communicate through the Pydantic models in
backend/schemas.py, never through raw text.
"""
