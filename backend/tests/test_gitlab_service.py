import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import RawItem
from app.services.gitlab_service import GitLabService
from app.services.settings_service import SettingsService


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_gitlab_sync_imports_issues_and_merge_requests_once(db_session: Session) -> None:
    settings = SettingsService(db_session)
    settings.set_gitlab_enabled(True)
    settings.set_gitlab_projects("group/project")
    settings.set_gitlab_auto_process(False)

    client = FakeGitLabClient()
    result = asyncio.run(GitLabService(db_session).sync(auto_process=False, client=client))
    duplicate_result = asyncio.run(GitLabService(db_session).sync(auto_process=False, client=client))

    assert result["imported_count"] == 2
    assert result["skipped_count"] == 0
    assert duplicate_result["imported_count"] == 0
    assert duplicate_result["skipped_count"] == 2
    assert db_session.query(RawItem).count() == 2
    issue = db_session.query(RawItem).filter(RawItem.source_uri == "gitlab:group/project:issue:7").one()
    assert issue.source_type == "gitlab"
    assert issue.title == "Project issue #7: Fix importer"
    assert "GitLab issue: Fix importer" in issue.body_text
    assert issue.metadata_json["gitlab"]["project_path"] == "group/project"


class FakeGitLabClient:
    def get_project(self, project_path: str) -> dict:
        return {"id": 123, "name": "Project", "path_with_namespace": project_path}

    def list_project_records(self, project_path: str, collection: str, max_results: int) -> list[dict]:
        if collection == "issues":
            return [
                {
                    "id": 1007,
                    "iid": 7,
                    "title": "Fix importer",
                    "description": "Importer drops labels.",
                    "state": "opened",
                    "labels": ["bug"],
                    "assignees": [{"name": "Riley"}],
                    "author": {"name": "Alex"},
                    "web_url": "https://gitlab.example/group/project/-/issues/7",
                    "updated_at": "2026-06-22T12:00:00Z",
                }
            ]
        return [
            {
                "id": 2003,
                "iid": 3,
                "title": "Add sync button",
                "description": "Adds a sync button.",
                "state": "opened",
                "labels": ["feature"],
                "assignees": [],
                "author": {"username": "dev"},
                "web_url": "https://gitlab.example/group/project/-/merge_requests/3",
                "updated_at": "2026-06-22T13:00:00Z",
            }
        ]
