"""File responsibility: Repository header widget with path label and action buttons."""

from collections.abc import Callable

from ....domain.git.models import GitRepository
from ....qt import QtCore, QtGui, QtWidgets
from ....resources import get_icon_path
from ....utils import term, translate
from ..widgets.buttons import make_tool_button
from ..widgets.styles import HEADER_ICON_BUTTON_STYLE, REPOSITORY_LABEL_EMPTY_STYLE, REPOSITORY_LABEL_LINK_STYLE


_REFRESH_ICON: QtGui.QIcon = QtGui.QIcon(str(get_icon_path("RefreshRepository.svg")))
_SAVE_ITERATION_ICON: QtGui.QIcon = QtGui.QIcon(str(get_icon_path("Commit.svg")))


class _ClickableRepositoryLabel(QtWidgets.QLabel):
    """Open repository directory when user clicks rendered project label."""

    def __init__(self, get_path: Callable[[], str | None]) -> None:
        super().__init__("")
        self._get_path = get_path

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Open repository directory on left click."""

        # Only left-click should trigger external navigation.
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.open_repository_directory()

        super().mousePressEvent(event)

    def open_repository_directory(self) -> None:
        """Open current repository path in desktop file browser."""
        path = self._get_path()

        # Missing repository path means label is informational only.
        if path:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))


class RepositoryHeader(QtWidgets.QWidget):
    """Render repository label plus refresh and save-iteration buttons."""

    refresh_requested = QtCore.Signal()
    save_iteration_requested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_repository_path: str | None = None
        self._setup_ui()

    def open_repository_directory(self) -> None:
        """Open current repository directory when one is displayed."""
        self._repository_label.open_repository_directory()

    def show_repository(self, repo: GitRepository | None) -> None:
        """Render repository name and path state in header label."""

        # Null repository means workbench currently has no project context.
        if repo is None:
            self._current_repository_path = None
            self._repository_label.setText(
                term(translate("History", "No project detected"), translate("History", "No repository detected"))
            )
            self._repository_label.setToolTip("")
            self._repository_label.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self._repository_label.setStyleSheet(REPOSITORY_LABEL_EMPTY_STYLE)
            return

        self._current_repository_path = repo.absolute_path
        text = term(translate("History", "Project: %1"), translate("History", "Repository: %1")).replace(
            "%1", repo.name
        )
        self._repository_label.setText(text)
        self._repository_label.setToolTip(repo.absolute_path)
        self._repository_label.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._repository_label.setStyleSheet(REPOSITORY_LABEL_LINK_STYLE)

    def _setup_ui(self) -> None:
        """Build repository header controls and layout."""
        self._repository_label = _ClickableRepositoryLabel(self._get_repository_path)
        self._repository_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self._repository_label.setStyleSheet(REPOSITORY_LABEL_EMPTY_STYLE)

        self._refresh_button = make_tool_button(
            tooltip=term(
                translate("History", "Refresh Project and Iterations"),
                translate("History", "Refresh Repository and Commits"),
            ),
            style=HEADER_ICON_BUTTON_STYLE,
            icon_size=QtCore.QSize(24, 24),
            tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
        )
        self._refresh_button.setIcon(_REFRESH_ICON)
        self._refresh_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self._refresh_button.clicked.connect(self.refresh_requested.emit)

        self._save_iteration_button = make_tool_button(
            tooltip=term(translate("History", "Save Iteration"), translate("History", "Commit")),
            style=HEADER_ICON_BUTTON_STYLE,
            icon_size=QtCore.QSize(24, 24),
            tool_button_style=QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly,
        )
        self._save_iteration_button.setIcon(_SAVE_ITERATION_ICON)
        self._save_iteration_button.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._save_iteration_button.clicked.connect(self.save_iteration_requested.emit)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._repository_label, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()
        layout.addWidget(self._save_iteration_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._refresh_button, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

    def _get_repository_path(self) -> str | None:
        """Return current repository absolute path."""
        return self._current_repository_path
