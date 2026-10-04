# File responsibility: Test native History registration, MDI geometry, lifetime cleanup, and deferred focus.
"""Workbench lifecycle tests using real Qt widgets at the native FreeCAD API boundary."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol, cast
from unittest.mock import Mock, patch

import pytest

from freecad.history_wb.qt import QtCore, QtWidgets
from freecad.history_wb.ui.registry import ui_registry
from freecad.history_wb.ui.state import ApplicationState
from freecad.history_wb.ui.views.diff_panel.view import HistoryPanelView


class _WorkbenchLike(Protocol):
    """Public workbench operation exercised by lifecycle tests."""

    def create_or_show_diff_panel(self) -> None:
        """Open or activate the History panel."""
        ...


class _NativeMainWindow(QtWidgets.QMainWindow):
    """Model native handles and Qt ownership, without emulating FreeCAD overlays."""

    def __init__(self) -> None:
        super().__init__()
        self.mdi_area = QtWidgets.QMdiArea(self)
        self.mdi_area.setViewMode(QtWidgets.QMdiArea.ViewMode.TabbedView)
        self.mdi_area.setOption(QtWidgets.QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation, False)
        self.setCentralWidget(self.mdi_area)
        self.resize(1500, 900)
        self.windows: dict[object, QtWidgets.QMainWindow] = {}
        self.activation_requests: list[object] = []

    def addWindow(self, proxy: HistoryPanelView) -> object:
        """Wrap the proxy widget in a native host and return an opaque view handle."""
        native_window = self.add_native_window(proxy.widget())
        handle = object()
        self.windows[handle] = native_window
        native_window.destroyed.connect(lambda: self.windows.pop(handle))
        return handle

    def add_native_window(self, widget: QtWidgets.QWidget) -> QtWidgets.QMainWindow:
        """Embed a native host using FreeCAD's first-view and subsequent-view showing sequence."""
        native_window = QtWidgets.QMainWindow()
        native_window.setWindowTitle(widget.windowTitle())
        native_window.setCentralWidget(widget)
        native_window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        shell = self.mdi_area.addSubWindow(native_window)
        shell.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

        # FreeCAD maximizes its first native view; Qt manages activation of later views.
        if len(self.mdi_area.subWindowList()) == 1:
            native_window.showMaximized()
        else:
            native_window.show()
        return native_window

    def setActiveWindow(self, handle: object) -> None:
        """Activate the current MDI shell owning the registered native view."""
        native_window = self.windows[handle]
        shell = native_window.parentWidget()
        assert isinstance(shell, QtWidgets.QMdiSubWindow)
        self.activation_requests.append(handle)
        self.mdi_area.setActiveSubWindow(shell)


@dataclass
class _WorkbenchHarness:
    """Observable native API and panel-composition collaborators for one workbench."""

    workbench: _WorkbenchLike
    main_window: _NativeMainWindow
    compose_panel: Mock
    panels: list[HistoryPanelView]
    focus_callbacks: list[Callable[[], None]]
    queued_callbacks: list[Callable[[], None]]
    application_state: ApplicationState
    command_presenter: Mock


@pytest.fixture(scope="session")
def application() -> QtWidgets.QApplication:
    """Share the QApplication with UI tests, including entrypoints-only runs."""
    app = QtWidgets.QApplication.instance()

    # Focused entrypoint runs do not load the UI directory's QApplication fixture.
    if app is None:
        app = QtWidgets.QApplication([])
    assert isinstance(app, QtWidgets.QApplication)
    return app


@pytest.fixture
def workbench_harness(
    application: QtWidgets.QApplication, monkeypatch: pytest.MonkeyPatch
) -> Iterator[_WorkbenchHarness]:
    """Load a fresh workbench under scoped FreeCADGui and native-window boundaries."""
    ui_registry.clear()
    state = ApplicationState(git_repository=None)
    command_presenter = Mock()
    ui_registry.register_application_state(state)
    ui_registry.register_workbench_command_presenter(command_presenter)
    main_window = _NativeMainWindow()
    main_window.show()
    panels: list[HistoryPanelView] = []
    focus_callbacks: list[Callable[[], None]] = []
    queued_callbacks: list[Callable[[], None]] = []

    def compose_panel(
        _container: object, _state: ApplicationState, focus_callback: Callable[[], None]
    ) -> HistoryPanelView:
        """Register new panel-scoped collaborators and capture their public focus callback."""
        panel = HistoryPanelView()
        panels.append(panel)
        focus_callbacks.append(focus_callback)
        ui_registry.register_diff_presenter(Mock())
        ui_registry.register_git_repository_presenter(Mock())
        return panel

    compose_mock = Mock(side_effect=compose_panel)
    monkeypatch.setattr("freecad.history_wb._container._container", Mock())
    monkeypatch.setattr("freecad.history_wb.ui.composer.compose_and_register_panel", compose_mock)
    fake_gui = ModuleType("FreeCADGui")
    fake_gui.Workbench = object  # type: ignore[attr-defined]
    fake_gui.getMainWindow = lambda: main_window  # type: ignore[attr-defined]
    module_name = "freecad.history_wb.entrypoints.workbench"
    spec = importlib.util.find_spec(module_name)
    assert spec is not None
    assert spec.loader is not None
    workbench_module = importlib.util.module_from_spec(spec)

    # Use a fresh module rather than mutating a cached module used by preference tests.
    with (
        patch.dict(sys.modules, {"FreeCADGui": fake_gui, module_name: workbench_module}),
        patch.object(
            QtCore.QTimer, "singleShot", side_effect=lambda _delay, callback: queued_callbacks.append(callback)
        ),
    ):
        spec.loader.exec_module(workbench_module)
        workbench = cast(_WorkbenchLike, workbench_module.HistoryWorkbench())
        try:
            yield _WorkbenchHarness(
                workbench=workbench,
                main_window=main_window,
                compose_panel=compose_mock,
                panels=panels,
                focus_callbacks=focus_callbacks,
                queued_callbacks=queued_callbacks,
                application_state=state,
                command_presenter=command_presenter,
            )
        finally:
            main_window.mdi_area.closeAllSubWindows()
            main_window.close()
            main_window.deleteLater()
            _flush_deferred_deletes(application)
            ui_registry.clear()


def _flush_deferred_deletes(application: QtWidgets.QApplication) -> None:
    """Deliver Qt destruction signals before observing close-lifecycle outcomes."""
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    application.processEvents()


def _native_window(harness: _WorkbenchHarness) -> tuple[object, QtWidgets.QMainWindow]:
    """Return the sole registered native view from the FreeCAD boundary."""
    assert len(harness.main_window.windows) == 1
    return next(iter(harness.main_window.windows.items()))


def _shell(native_window: QtWidgets.QMainWindow) -> QtWidgets.QMdiSubWindow:
    """Return the native host's current Qt MDI shell."""
    shell = native_window.parentWidget()
    assert isinstance(shell, QtWidgets.QMdiSubWindow)
    return shell


def test_panel_registers_with_native_title_and_reuses_native_activation(workbench_harness: _WorkbenchHarness) -> None:
    """Opening History registers its titled proxy once; reopening activates its native handle."""
    harness = workbench_harness
    harness.workbench.create_or_show_diff_panel()
    handle, native_window = _native_window(harness)
    assert native_window.centralWidget() is harness.panels[0]
    assert native_window.windowTitle() == "History"
    assert _shell(native_window).isVisible()

    other_shell = harness.main_window.mdi_area.addSubWindow(QtWidgets.QWidget())
    other_shell.show()
    harness.main_window.mdi_area.setActiveSubWindow(other_shell)
    harness.main_window.activation_requests.clear()
    harness.workbench.create_or_show_diff_panel()

    harness.compose_panel.assert_called_once()
    assert harness.main_window.activation_requests == [handle]
    assert harness.main_window.mdi_area.activeSubWindow() is _shell(native_window)


@pytest.mark.parametrize("previous_tab", ["3D", "Page"])
def test_tabbed_history_covers_viewport_with_other_native_document_tabs(
    workbench_harness: _WorkbenchHarness, application: QtWidgets.QApplication, previous_tab: str
) -> None:
    """Opening or refocusing maximized History covers other native tabs without shrinking its shell."""
    harness = workbench_harness
    mdi_area = harness.main_window.mdi_area
    document_tabs = {title: harness.main_window.add_native_window(QtWidgets.QLabel(title)) for title in ["3D", "Page"]}
    mdi_area.setActiveSubWindow(_shell(document_tabs[previous_tab]))
    application.processEvents()
    assert mdi_area.activeSubWindow() is _shell(document_tabs[previous_tab])

    harness.workbench.create_or_show_diff_panel()
    _, native_window = _native_window(harness)
    history_shell = _shell(native_window)
    assert mdi_area.activeSubWindow() is history_shell
    assert history_shell.isMaximized()
    assert history_shell.geometry().contains(mdi_area.viewport().rect())

    mdi_area.setActiveSubWindow(_shell(document_tabs["Page"]))
    application.processEvents()
    harness.workbench.create_or_show_diff_panel()

    harness.compose_panel.assert_called_once()
    assert mdi_area.activeSubWindow() is history_shell
    assert history_shell.isMaximized()
    assert history_shell.geometry().contains(mdi_area.viewport().rect())


def test_normal_subwindow_history_preserves_native_geometry(
    workbench_harness: _WorkbenchHarness, application: QtWidgets.QApplication
) -> None:
    """Opening an unmaximized History view preserves geometry assigned by its native host."""
    harness = workbench_harness
    mdi_area = harness.main_window.mdi_area
    mdi_area.setViewMode(QtWidgets.QMdiArea.ViewMode.SubWindowView)
    document_window = harness.main_window.add_native_window(QtWidgets.QLabel("3D"))
    document_window.showNormal()
    application.processEvents()
    assert not _shell(document_window).isMaximized()

    native_geometry: list[QtCore.QRect] = []
    add_native_window = harness.main_window.addWindow

    def register_window(proxy: HistoryPanelView) -> object:
        """Record the native API's assigned geometry before workbench presentation."""
        handle = add_native_window(proxy)
        _, native_window = _native_window(harness)
        native_geometry.append(_shell(native_window).geometry())
        return handle

    with patch.object(harness.main_window, "addWindow", side_effect=register_window):
        harness.workbench.create_or_show_diff_panel()
    _, native_window = _native_window(harness)
    history_shell = _shell(native_window)

    assert mdi_area.activeSubWindow() is history_shell
    assert not history_shell.isMaximized()
    assert history_shell.geometry() == native_geometry[0]


def test_close_reopen_replaces_panel_presenters_and_preserves_application_components(
    workbench_harness: _WorkbenchHarness, application: QtWidgets.QApplication
) -> None:
    """Native close clears panel scope; reopen composes against the same application state."""
    harness = workbench_harness
    harness.workbench.create_or_show_diff_panel()
    old_handle, native_window = _native_window(harness)
    old_diff_presenter = ui_registry.diff_presenter
    old_repository_presenter = ui_registry.git_repository_presenter
    assert old_diff_presenter is not None
    assert old_repository_presenter is not None

    assert _shell(native_window).close()
    _flush_deferred_deletes(application)

    # Panel presenters cleared; application state and command presenter preserved.
    assert harness.main_window.windows == {}
    assert ui_registry.diff_presenter is None
    assert ui_registry.git_repository_presenter is None
    assert ui_registry.application_state is harness.application_state
    assert ui_registry.workbench_command_presenter is harness.command_presenter

    harness.workbench.create_or_show_diff_panel()
    new_handle, new_native_window = _native_window(harness)
    assert new_handle is not old_handle
    assert new_native_window.centralWidget() is harness.panels[1]
    assert ui_registry.diff_presenter is not None
    assert ui_registry.diff_presenter is not old_diff_presenter
    assert ui_registry.git_repository_presenter is not None
    assert ui_registry.git_repository_presenter is not old_repository_presenter
    assert all(call.args[1] is harness.application_state for call in harness.compose_panel.call_args_list)
    assert ui_registry.workbench_command_presenter is harness.command_presenter


def test_queued_focus_activates_the_registered_native_view(workbench_harness: _WorkbenchHarness) -> None:
    """Presenter-requested deferred focus activates History through the native handle API."""
    harness = workbench_harness
    harness.workbench.create_or_show_diff_panel()
    handle, native_window = _native_window(harness)
    other_shell = harness.main_window.mdi_area.addSubWindow(QtWidgets.QWidget())
    other_shell.show()
    harness.main_window.mdi_area.setActiveSubWindow(other_shell)
    harness.main_window.activation_requests.clear()

    harness.focus_callbacks[0]()
    assert harness.main_window.mdi_area.activeSubWindow() is other_shell
    assert len(harness.queued_callbacks) == 1
    harness.queued_callbacks.pop(0)()

    assert harness.main_window.activation_requests == [handle]
    assert harness.main_window.mdi_area.activeSubWindow() is _shell(native_window)


@pytest.mark.parametrize("reopen", [False, True], ids=["closed", "reopened"])
def test_queued_focus_from_closed_panel_does_not_activate_another_lifetime(
    workbench_harness: _WorkbenchHarness, application: QtWidgets.QApplication, reopen: bool
) -> None:
    """Queued focus from a closed History view cannot steal focus or activate its replacement."""
    harness = workbench_harness
    harness.workbench.create_or_show_diff_panel()
    _, native_window = _native_window(harness)
    harness.focus_callbacks[0]()
    assert len(harness.queued_callbacks) == 1
    assert _shell(native_window).close()
    _flush_deferred_deletes(application)

    # Exercise both an absent panel and a newly composed replacement lifetime.
    if reopen:
        harness.workbench.create_or_show_diff_panel()
    other_shell = harness.main_window.mdi_area.addSubWindow(QtWidgets.QWidget())
    other_shell.show()
    harness.main_window.mdi_area.setActiveSubWindow(other_shell)
    harness.main_window.activation_requests.clear()
    harness.queued_callbacks.pop(0)()

    assert harness.main_window.activation_requests == []
    assert harness.main_window.mdi_area.activeSubWindow() is other_shell


def test_mdi_shell_recreation_preserves_native_host_and_pending_focus(
    workbench_harness: _WorkbenchHarness, application: QtWidgets.QApplication
) -> None:
    """Replacing an MDI shell retains panel scope and pending focus for the same native host."""
    harness = workbench_harness
    harness.workbench.create_or_show_diff_panel()
    handle, native_window = _native_window(harness)
    diff_presenter = ui_registry.diff_presenter
    repository_presenter = ui_registry.git_repository_presenter
    harness.focus_callbacks[0]()
    old_shell = _shell(native_window)

    # FreeCAD can detach/re-embed a native view while disposing its old MDI shell.
    harness.main_window.mdi_area.removeSubWindow(native_window)
    new_shell = harness.main_window.mdi_area.addSubWindow(native_window)
    new_shell.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
    old_shell.deleteLater()
    _flush_deferred_deletes(application)

    assert harness.main_window.windows == {handle: native_window}
    assert ui_registry.diff_presenter is diff_presenter
    assert ui_registry.git_repository_presenter is repository_presenter
    harness.main_window.activation_requests.clear()
    harness.workbench.create_or_show_diff_panel()
    harness.queued_callbacks.pop(0)()

    harness.compose_panel.assert_called_once()
    assert harness.main_window.activation_requests == [handle, handle]
    assert new_shell.isVisible()
    assert harness.main_window.mdi_area.activeSubWindow() is new_shell
