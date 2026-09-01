"""File responsibility: Modal dialog helpers used by diff panel workflows."""

from __future__ import annotations

from dataclasses import dataclass

from ....domain.git.models import GitRepositoryInitCandidate
from ....qt import QtWidgets
from ....utils import term, translate
from ..widgets.buttons import make_dialog_button_box


@dataclass(frozen=True)
class GitConfigDialogResult:
    """Git identity configuration values collected from the user."""

    author_name: str
    author_email: str
    should_save_globally: bool


def show_save_iteration_dialog(parent: QtWidgets.QWidget) -> str | None:
    """Show Save Iteration dialog and return notes when accepted."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(term(translate("History", "Save Iteration"), translate("History", "Commit")))
    dialog.setSizeGripEnabled(True)

    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(
        term(translate("History", "Enter iteration notes:"), translate("History", "Enter commit notes:"))
    )
    layout.addWidget(label)

    text_edit = QtWidgets.QPlainTextEdit(dialog)
    text_edit.setPlaceholderText(
        term(
            translate("History", "Enter iteration notes (subject and optional body)..."),
            translate("History", "Enter commit notes (subject and optional body)..."),
        )
    )
    text_edit.setTabStopDistance(40)
    text_edit.setMinimumHeight(100)
    text_edit.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
    layout.addWidget(text_edit)

    button_box = make_dialog_button_box(
        accept_text=translate("History", "OK"),
        reject_text=translate("History", "Cancel"),
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    dialog.resize(500, 300)

    # Cancel path returns no notes so caller can abort save flow.
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return text_edit.toPlainText()


def show_configure_author_dialog(
    parent: QtWidgets.QWidget,
    message: str | None,
    initial_values: GitConfigDialogResult | None,
    global_config_writable: bool,
) -> GitConfigDialogResult | None:
    """Show configure-author dialog and return entered values."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(translate("History", "Configure Author"))
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(
        QtWidgets.QLabel(
            term(
                translate(
                    "History",
                    "Enter the name and email you'd like to use for your git identity, "
                    "which is used for authoring project iterations.",
                ),
                translate(
                    "History",
                    "Enter the name and email you'd like to use for your git identity, "
                    "which is used for authoring repository commits.",
                ),
            ),
            dialog,
        )
    )

    # Validation/configuration problems must stay visible above inputs.
    if message:
        message_label = QtWidgets.QLabel(message, dialog)
        message_label.setStyleSheet("color: red;")
        layout.addWidget(message_label)

    form_layout = QtWidgets.QFormLayout()
    name_edit = QtWidgets.QLineEdit(dialog)
    email_edit = QtWidgets.QLineEdit(dialog)
    remember_checkbox = QtWidgets.QCheckBox(
        term(
            translate("History", "Configure globally for all projects"),
            translate("History", "Configure globally for all repositories"),
        ),
        dialog,
    )

    # Existing values seed retry flow after validation or partial configuration.
    if initial_values is not None:
        name_edit.setText(initial_values.author_name)
        email_edit.setText(initial_values.author_email)
        remember_checkbox.setChecked(initial_values.should_save_globally)

    # Global option must be disabled when underlying git config file cannot be written.
    if not global_config_writable:
        remember_checkbox.setChecked(False)
        remember_checkbox.setEnabled(False)

    form_layout.addRow(translate("History", "Name:"), name_edit)
    form_layout.addRow(translate("History", "Email:"), email_edit)
    layout.addLayout(form_layout)
    layout.addWidget(remember_checkbox)

    # Explain disabled global option inline so user understands forced local save.
    if not global_config_writable:
        global_config_label = QtWidgets.QLabel(
            translate(
                "History",
                "Global configuration option disabled because global config file not writable.",
            ),
            dialog,
        )
        global_config_label.setStyleSheet("color: red;")
        layout.addWidget(global_config_label)

    button_box = make_dialog_button_box(
        accept_text=translate("History", "OK"),
        reject_text=translate("History", "Cancel"),
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    # Cancel path returns no identity so caller can abort flow cleanly.
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return GitConfigDialogResult(
        author_name=name_edit.text().strip(),
        author_email=email_edit.text().strip(),
        should_save_globally=remember_checkbox.isChecked(),
    )


def show_restore_file_confirmation_dialog(parent: QtWidgets.QWidget, git_path: str) -> bool:
    """Show destructive confirmation dialog for restore actions."""

    title = translate("History", "Restore")
    message = translate(
        "History",
        "This operation will overwrite the current file(s) on disk with the selected saved copies.\n\n"
        "All open FreeCAD documents will be closed and reopened to ensure links are updated.\n\n"
        "Unsaved changes in open files will be lost. Before proceeding, save any documents that will not be restored."
        "\n\nSaved history will not be affected.",
    )

    # Bulk restore uses empty path and should keep the generic warning text.
    if git_path:
        message = f"{git_path}\n\n{message}"

    restore_button_text = translate("History", "Restore")
    cancel_button_text = translate("History", "Cancel")
    dialog = QtWidgets.QMessageBox(parent)
    dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    dialog.setWindowTitle(title)
    dialog.setText(message)
    restore_button = dialog.addButton(restore_button_text, QtWidgets.QMessageBox.ButtonRole.DestructiveRole)
    dialog.addButton(cancel_button_text, QtWidgets.QMessageBox.ButtonRole.RejectRole)
    dialog.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Cancel)
    dialog.exec()
    return dialog.clickedButton() == restore_button


def show_restore_scope_dialog(parent: QtWidgets.QWidget) -> str | None:
    """Show bulk scope picker for restore-all action."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(translate("History", "Restore All"))
    dialog.setMinimumWidth(620)
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.setSpacing(10)
    title_label = QtWidgets.QLabel(translate("History", "Which files would you like to restore?"))
    title_label.setWordWrap(True)
    layout.addWidget(title_label)
    listed = QtWidgets.QRadioButton(translate("History", "Listed FreeCAD files"))
    listed_desc = QtWidgets.QLabel(
        term(
            translate(
                "History",
                "Restore only the FreeCAD files changed in the selected iteration. "
                "Other files on disk are left unchanged.",
            ),
            translate(
                "History",
                "Restore only the FreeCAD files changed in the selected commit. "
                "Other files on disk are left unchanged.",
            ),
        )
    )
    listed_desc.setWordWrap(True)
    all_fcstd = QtWidgets.QRadioButton(translate("History", "All FreeCAD files"))
    all_desc = QtWidgets.QLabel(
        translate(
            "History",
            "Restore all saved FreeCAD files to their state in this history entry. "
            "Saved FreeCAD files that did not exist in this entry will be removed. "
            "Files that have not been saved to history will be kept.",
        )
    )
    all_desc.setWordWrap(True)
    listed_desc.setIndent(22)
    all_desc.setIndent(22)
    scope_group = QtWidgets.QButtonGroup(dialog)
    scope_group.setExclusive(True)
    scope_group.addButton(listed)
    scope_group.addButton(all_fcstd)
    listed.setChecked(True)

    listed_group = QtWidgets.QWidget(dialog)
    listed_group_layout = QtWidgets.QVBoxLayout(listed_group)
    listed_group_layout.setContentsMargins(0, 0, 0, 0)
    listed_group_layout.setSpacing(2)
    listed_group_layout.addWidget(listed)
    listed_group_layout.addWidget(listed_desc)

    all_group = QtWidgets.QWidget(dialog)
    all_group_layout = QtWidgets.QVBoxLayout(all_group)
    all_group_layout.setContentsMargins(0, 0, 0, 0)
    all_group_layout.setSpacing(2)
    all_group_layout.addWidget(all_fcstd)
    all_group_layout.addWidget(all_desc)

    layout.addWidget(listed_group)
    layout.addWidget(all_group)
    buttons = make_dialog_button_box(
        accept_text=translate("History", "Restore"),
        reject_text=translate("History", "Cancel"),
    )
    cancel_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)

    # Cancel stays default so Enter does not trigger destructive restore accidentally.
    if cancel_button is not None:
        cancel_button.setDefault(True)
        cancel_button.setAutoDefault(True)

    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.resize(700, dialog.sizeHint().height())

    # Cancel path returns no scope so caller can abort restore flow.
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return "listed_fcstd" if listed.isChecked() else "all_fcstd"


def show_init_repository_dialog(
    parent: QtWidgets.QWidget,
    candidates: list[GitRepositoryInitCandidate],
) -> str | None:
    """Show repository initialization dialog and return selected directory."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(
        term(translate("History", "Initialize Project"), translate("History", "Initialize Repository"))
    )
    dialog.setSizeGripEnabled(True)
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(
        QtWidgets.QLabel(
            term(
                translate(
                    "History",
                    "Choose a directory to initialize based on currently open documents. "
                    "The selected directory will be the root of your project:",
                ),
                translate(
                    "History",
                    "Choose a directory to initialize based on currently open documents. "
                    "The selected directory will be the root of your repository:",
                ),
            )
        )
    )

    button_group = QtWidgets.QButtonGroup(dialog)
    first_available_button: QtWidgets.QRadioButton | None = None

    for index, candidate in enumerate(candidates):
        row_layout = QtWidgets.QHBoxLayout()
        radio = QtWidgets.QRadioButton(candidate.path, dialog)
        radio.setEnabled(candidate.is_available)
        button_group.addButton(radio, index)
        row_layout.addWidget(radio)
        if candidate.is_available and first_available_button is None:
            first_available_button = radio

        if not candidate.is_available:
            reason_label = QtWidgets.QLabel(
                term(
                    translate("History", "Already inside project"),
                    translate("History", "Already inside repository"),
                ),
                dialog,
            )
            reason_label.setEnabled(False)
            row_layout.addWidget(reason_label)

        row_layout.addStretch()
        layout.addLayout(row_layout)

    if first_available_button is not None:
        first_available_button.setChecked(True)
    else:
        no_available_text = term(
            translate("History", "All listed directories are already inside projects."),
            translate("History", "All listed directories are already inside repositories."),
        )
        layout.addWidget(QtWidgets.QLabel(no_available_text))

    button_layout = QtWidgets.QHBoxLayout()
    initialize_button = QtWidgets.QPushButton(translate("History", "Initialize"))
    initialize_button.setEnabled(first_available_button is not None)
    cancel_button = QtWidgets.QPushButton(translate("History", "Cancel"))
    initialize_button.clicked.connect(dialog.accept)
    cancel_button.clicked.connect(dialog.reject)

    button_layout.addStretch()
    button_layout.addWidget(initialize_button)
    button_layout.addWidget(cancel_button)
    layout.addLayout(button_layout)

    dialog.setMinimumWidth(680)
    dialog.adjustSize()
    target_height = min(360, dialog.sizeHint().height() + 8)
    dialog.resize(dialog.width(), target_height)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    selected_id = button_group.checkedId()
    if selected_id < 0:
        return None
    return candidates[selected_id].path


def show_gitignore_editor_dialog(parent: QtWidgets.QWidget, content: str) -> str | None:
    """Show gitignore editor dialog. Returns edited content on accept, None on cancel."""
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle(term(translate("History", "Edit Ignored Files"), translate("History", "Edit .gitignore")))
    dialog.setMinimumWidth(680)
    dialog.setMinimumHeight(460)

    layout = QtWidgets.QVBoxLayout(dialog)
    help_template = translate(
        "History",
        'Update the ignored files list. Lines starting with a "#" are considered comments. '
        'Click <a href="%1">here</a> to learn about the full syntax.',
    )
    help_label = QtWidgets.QLabel(help_template.replace("%1", "https://www.w3schools.com/git/git_ignore.asp"))
    help_label.setOpenExternalLinks(True)
    layout.addWidget(help_label)

    text_edit = QtWidgets.QPlainTextEdit(dialog)
    text_edit.setPlainText(content)
    layout.addWidget(text_edit)

    button_box = make_dialog_button_box(
        accept_text=translate("History", "Save"),
        reject_text=translate("History", "Cancel"),
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None

    return text_edit.toPlainText()
