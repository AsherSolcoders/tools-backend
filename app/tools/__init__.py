"""Config-driven tool engine.

Importing this package registers every tool processor (via the @register
decorators in the *_tools modules) and exposes the populated registry.
"""
from app.tools import calculators, developer_tools, image_tools, pdf_tools, text_tools  # noqa: F401
from app.tools.registry import REGISTRY, get_processor, get_tool, list_categories, list_tools

__all__ = [
    "REGISTRY",
    "get_tool",
    "get_processor",
    "list_tools",
    "list_categories",
]
