"""
apifunc package initialization.
"""

from ._version import __version__

# Import main functionality to make it available at package level
from .apifunc import *
from .html_to_pdf import *
from .json_to_html import *
from .cli import *

# Define what should be available when using `from apifunc import *`
__all__ = []
