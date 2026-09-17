# File responsibility: Tests for dependency injection container composition.

from freecad.history_wb.application.container import (
    ApplicationContainer,
    create_application_container,
)
from freecad.history_wb.domain.freecad_ports import FreeCadContext
from freecad.history_wb.domain.git.models import GitRepository


class _FakeParamGroup:
    """In-memory stand-in for FreeCAD's parameter group."""

    def GetString(self, key: str, default: str = "") -> str:  # noqa: N802
        return default

    def SetString(self, key: str, value: str) -> None:  # noqa: N802
        return None

    def GetBool(self, key: str, default: bool = False) -> bool:  # noqa: N802
        return default

    def SetBool(self, key: str, value: bool) -> None:  # noqa: N802
        return None

    def GetInt(self, key: str, default: int = 0) -> int:  # noqa: N802
        return default

    def SetInt(self, key: str, value: int) -> None:  # noqa: N802
        return None


class _FakeApp:
    """Minimal FreeCAD app stand-in exposing the parameter system."""

    def ParamGet(self, path: str) -> _FakeParamGroup:  # noqa: N802
        return _FakeParamGroup()


def _make_ctx() -> FreeCadContext:
    return FreeCadContext(app=_FakeApp(), gui=object())  # type: ignore[arg-type]


def test_container_returns_wired_application_container() -> None:
    """create_application_container returns an ApplicationContainer with key public actions."""
    ctx = _make_ctx()
    container = create_application_container(ctx)

    assert isinstance(container, ApplicationContainer)
    assert container.create_document_diffs_action is not None
    assert container.stage_documents_action is not None
    assert container.unstage_documents_action is not None
    assert container.find_active_git_repository_action is not None
    assert container.get_gitignore_content_action is not None
    assert container.update_gitignore_action is not None
    assert container.get_commits_action is not None
    assert container.open_all_documents_in_repository_action is not None
    assert container.recompute_all_open_documents_action is not None
    assert container.settings_repo is not None


def test_get_commits_action_executes_through_container() -> None:
    """GetCommitsAction executes successfully through the container."""
    ctx = _make_ctx()
    container = create_application_container(ctx)

    repo = GitRepository(name="test_project", absolute_path="/home/user/dir/test_project")
    result = container.get_commits_action.execute(repo=repo)

    assert result is not None
    assert result.is_success is True
    assert result.data == []

