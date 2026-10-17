"""Compatibility import; DAIL owns the cell-link implementation in its fork."""

from scripts.common.sources import load_integration

CellLinkConnection = load_integration(
    "dail_sql", "reproduction_cell_link_cache.py"
).CellLinkConnection
