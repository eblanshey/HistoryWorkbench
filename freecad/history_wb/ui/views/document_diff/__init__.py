"""Module responsibility: Document diff panel facade and extracted child widgets."""

from .diff_row import DiffTreeRowWidget
from .document_row import REMOVE_REVIEWED_TOOLTIP, DocumentDiffRowWidget
from .panel import DocumentDiffTreeWidget
from .status_indicators import DocumentStatusIndicatorsWidget
from .summary_bar import DocumentDiffSummaryBar
from .tree import DocumentDiffTree
from .tree_items import build_document_root_item, build_node_item


__all__ = [
    "DocumentDiffRowWidget",
    "DiffTreeRowWidget",
    "DocumentDiffTree",
    "DocumentDiffSummaryBar",
    "DocumentDiffTreeWidget",
    "DocumentStatusIndicatorsWidget",
    "REMOVE_REVIEWED_TOOLTIP",
    "build_document_root_item",
    "build_node_item",
]
