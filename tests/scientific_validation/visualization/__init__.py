"""
Visualization engine for scientific validation results.

Generates plots, charts, and dashboards for publication-quality reports.
"""

from .plots import PlotGenerator
from .dashboard import DashboardGenerator
from .figures import FigureGenerator

__all__ = [
    "PlotGenerator",
    "DashboardGenerator",
    "FigureGenerator",
]
