"""Agentic ingestion engine.

Point it at a data source; it classifies each item, chooses or authors a recipe
(how to process that class), executes the recipe deterministically, remembers
what it did, and traces everything. See PROJECT.md for the full flow.
"""

__version__ = "0.1.0"
