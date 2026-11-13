"""Source distribution and wheel metadata parity checker."""
__version__ = "0.1.1"
from .core import ArtifactError, Finding, Report, compare, locate_distributions
__all__ = ["ArtifactError", "Finding", "Report", "compare", "locate_distributions"]
