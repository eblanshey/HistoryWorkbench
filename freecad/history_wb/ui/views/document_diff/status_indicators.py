"""File responsibility: Document-row status indicator widgets and open-document action routing."""

from __future__ import annotations

from ....qt import QtCore, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import DocumentStatusIndicator, WorkingTreeDocumentClosedIndicator
from ..theme.buttons import set_action_button_style
from ..widgets.styles import TREE_ITEM_HEIGHT, TREE_ITEM_ICON_SIZE


class DocumentStatusIndicatorsWidget(QtWidgets.QWidget):
    """Render document status indicators and emit open-document actions."""

    open_document_requested = QtCore.Signal(str)  # git_path

    def __init__(
        self,
        indicators: list[DocumentStatusIndicator],
        git_path: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._indicators = indicators
        self._git_path = git_path
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("documentStatusIndicators")
        self.setStyleSheet(
            "QWidget#documentStatusIndicators { background-color: transparent; } "
            "QWidget#documentStatusIndicators QLabel { background-color: transparent; }"
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for indicator in self._indicators:
            # Closed working-tree files need a button because user can resolve issue in-place.
            if isinstance(indicator, WorkingTreeDocumentClosedIndicator):
                layout.addWidget(self._create_open_document_button(indicator))
                continue

            layout.addWidget(self._create_icon_label(indicator))

    def _create_icon_label(self, indicator: DocumentStatusIndicator) -> QtWidgets.QLabel:
        """Create passive icon label for non-interactive document status."""
        icon_label = QtWidgets.QLabel()
        icon_label.setPixmap(indicator.icon.pixmap(16, 16))
        icon_label.setToolTip(translate("History", indicator.tooltip))
        return icon_label

    def _create_open_document_button(self, indicator: WorkingTreeDocumentClosedIndicator) -> QtWidgets.QPushButton:
        """Create button that opens a closed working-tree document for comparison."""
        button = QtWidgets.QPushButton(self)
        button.setIcon(indicator.icon)
        button.setText(translate("History", "Open"))
        button.setIconSize(QtCore.QSize(TREE_ITEM_ICON_SIZE, TREE_ITEM_ICON_SIZE))
        button.setToolTip(translate("History", indicator.tooltip))
        button.setFixedHeight(TREE_ITEM_HEIGHT)
        button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        set_action_button_style(button)
        button.clicked.connect(lambda checked=False: self.open_document_requested.emit(self._git_path))
        return button
