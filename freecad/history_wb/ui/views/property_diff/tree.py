"""File responsibility: Property diff tree container that wires headers, delegate, and item builders."""

from __future__ import annotations

from ....domain.config import FLOAT_PRECISION as DEFAULT_FLOAT_PRECISION
from ....domain.diff.models import DiffState
from ....domain.settings import SettingsRepository
from ....qt import QtCore, QtGui, QtWidgets
from ....utils import translate
from ...presenters.presentation_models import PropertyPresentation
from ..theme.diff import colors_for_diff_state
from .cell import PropertyDiffCellWidget
from .delegate import PropertyValueDelegate
from .tree_items import PROPERTY_DIFF_STATE_ROLE, apply_stored_expansion_state, build_grouped_property_items


__all__ = ["PropertyDiffTreeWidget"]


class PropertyDiffTreeWidget(QtWidgets.QTreeWidget):
    """Widget that renders grouped property diffs in three columns."""

    def __init__(
        self,
        parent: QtWidgets.QWidget | None = None,
        settings_repo: SettingsRepository | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_repo = settings_repo
        self._default_precision = DEFAULT_FLOAT_PRECISION
        self._refreshing_style = False
        self._property_value_delegate = PropertyValueDelegate(self)
        self._theme_probe = QtWidgets.QLabel(self)
        self._theme_probe.hide()
        self._setup_tree()

    def _setup_tree(self) -> None:
        """Configure headers, resize behavior, delegate, and edit triggers."""
        self.setObjectName("propertyDiffTree")
        self.setColumnCount(3)
        self.setHeaderLabels(
            [
                translate("History", "Property"),
                translate("History", "Old Value"),
                translate("History", "New Value"),
            ]
        )
        self.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.header().setStretchLastSection(True)
        self.setItemDelegate(self._property_value_delegate)
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self.currentItemChanged.connect(self._on_current_item_changed)
        self._refresh_diff_stylesheet()

    def _refresh_diff_stylesheet(self) -> None:
        """Apply one shared stylesheet for every highlighted property cell."""
        if self._refreshing_style:
            return

        # Stylesheet themes such as OpenTheme add borders and rounded corners
        # to native items. Text lives in labels, so normalize the item box and
        # let cell widgets own all visible borders and backgrounds consistently.
        item_selector = "QTreeWidget#propertyDiffTree::item"
        rules = [
            f"{item_selector} {{ border: none; border-radius: 0px; }}",
            f"{item_selector}:selected {{ border: none; border-radius: 0px; }}",
            f"{item_selector}:hover {{ border: none; border-radius: 0px; }}",
        ]
        palette = self._effective_diff_palette()
        for state in (DiffState.ADDED, DiffState.DELETED, DiffState.MODIFIED):
            colors = colors_for_diff_state(state, palette)
            if colors.normal_background is None:
                raise RuntimeError("Changed property state requires a background color")
            selector = f'QTreeWidget#propertyDiffTree QLabel#propertyDiffCell[diffState="{state.name}"]'
            rules.extend(
                [
                    f"{selector} {{ background-color: {colors.normal_background.name()}; "
                    f"color: {colors.normal_foreground.name()}; padding: 0px 3px; "
                    f"border: none; border-radius: 0px; }}",
                    f"{selector}:hover {{ background-color: {colors.hover_background.name()}; "
                    f"color: {colors.hover_foreground.name()}; }}",
                    f'{selector}[rowSelected="true"] {{ background-color: {colors.selected_background.name()}; '
                    f"color: {colors.selected_foreground.name()}; }}",
                ]
            )

        # setStyleSheet emits StyleChange synchronously, which would recursively refresh this stylesheet.
        self._refreshing_style = True
        try:
            self.setStyleSheet(" ".join(rules))
        finally:
            self._refreshing_style = False

    def _effective_diff_palette(self) -> QtGui.QPalette:
        """Combine tree surfaces with foreground resolved through application QSS.

        Stylesheet themes can paint label text without updating the tree's Text
        palette role. A polished QLabel exposes the effective WindowText color,
        which keeps light/dark diff accent selection aligned with visible text.
        """
        self._theme_probe.ensurePolished()
        palette = QtGui.QPalette(self.palette())
        palette.setColor(
            QtGui.QPalette.ColorRole.Text,
            self._theme_probe.palette().color(QtGui.QPalette.ColorRole.WindowText),
        )
        return palette

    def changeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Refresh shared semantic colors when FreeCAD changes theme or style."""
        super().changeEvent(event)
        if event.type() in {
            QtCore.QEvent.Type.ApplicationPaletteChange,
            QtCore.QEvent.Type.PaletteChange,
            QtCore.QEvent.Type.StyleChange,
        }:
            self._refresh_diff_stylesheet()

    def clear_property_diff(self) -> None:
        """Clear all property diff entries from the tree widget."""
        self.clear()

    def show_property_diff(self, properties: list[PropertyPresentation]) -> None:
        """Render property diffs grouped by their group name."""
        updates_enabled = self.updatesEnabled()

        # Defer repaints while installing many items and cell widgets to avoid repeated layout and style work.
        self.setUpdatesEnabled(False)
        try:
            self.clear_property_diff()
            if not properties:
                return

            items = build_grouped_property_items(properties, self._get_precision())
            self.addTopLevelItems(items)
            for group_item in items:
                self._install_group_header_widget(group_item)
                self._install_property_widgets(group_item)
            apply_stored_expansion_state(items)
        finally:
            self.setUpdatesEnabled(updates_enabled)

    def _install_group_header_widget(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Render group text through QLabel so stylesheet themes control its foreground."""
        text = item.text(0)
        item.setText(0, "")
        label = QtWidgets.QLabel(text, self)
        label.setObjectName("propertyDiffGroup")
        label.setAccessibleName(text)
        label.setFont(item.font(0))
        self.setItemWidget(item, 0, label)

    def _install_property_widgets(self, parent: QtWidgets.QTreeWidgetItem) -> None:
        """Install selectable cell widgets for every property row, then recurse."""
        for index in range(parent.childCount()):
            item = parent.child(index)
            state = item.data(0, PROPERTY_DIFF_STATE_ROLE)
            if not isinstance(state, DiffState):
                raise RuntimeError("Property row requires semantic diff state")
            self._install_row_widgets(item, state)
            self._install_property_widgets(item)

    def _install_row_widgets(
        self,
        item: QtWidgets.QTreeWidgetItem,
        state: DiffState,
    ) -> None:
        """Replace visible item text with three shared-style cell widgets."""
        for column in range(self.columnCount()):
            text = item.text(column)

            # Installed labels own visible and accessible text because themes
            # such as OpenTheme style QLabel and native item text differently.
            # Native items still provide branch and selection backgrounds.
            item.setText(column, "")
            cell = PropertyDiffCellWidget(
                self,
                item,
                text,
                state,
                tooltip=item.toolTip(column),
            )
            self.setItemWidget(item, column, cell)

    def _on_current_item_changed(
        self,
        current: QtWidgets.QTreeWidgetItem | None,
        previous: QtWidgets.QTreeWidgetItem | None,
    ) -> None:
        """Apply tree selection state to highlighted cell widgets."""
        for item, selected in ((previous, False), (current, True)):
            if item is None:
                continue
            for cell in self._row_cells(item):
                cell.set_row_selected(selected)

    def _row_cells(self, item: QtWidgets.QTreeWidgetItem) -> list[PropertyDiffCellWidget]:
        """Return installed highlighted cells for one item."""
        cells: list[PropertyDiffCellWidget] = []
        for column in range(self.columnCount()):
            widget = self.itemWidget(item, column)
            if isinstance(widget, PropertyDiffCellWidget):
                cells.append(widget)
        return cells

    def _get_precision(self) -> int:
        """Read configured float precision or fall back to default precision."""
        if self._settings_repo is not None:
            try:
                return self._settings_repo.get_settings().float_precision
            except (AttributeError, RuntimeError):
                pass
        return self._default_precision
