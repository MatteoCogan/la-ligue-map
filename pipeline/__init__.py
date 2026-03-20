"""
Pipeline La Ligue - Transform & Upload to map-making.app
"""

__version__ = "1.0.0"
__author__ = "Matteo"
__description__ = "Transform coordinatesAllTags.json to map-making.app format"

from .main import Pipeline

__all__ = ["Pipeline"]
