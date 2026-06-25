import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models import RawItem
from app.services.github_service import GitHubService
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


def test_github_sync_imports_issues_and_pull_requests_once(db_session: Session) -> None:
    settings = SettingsService(db_session)
    settings.set_github_enabled(True)
    settings.set_github_repositories("owner/repo")
    settings.set_github_auto_process(False)

    client = FakeGitHubClient()
    result = asyncio.run(GitHubService(db_session).sync(auto_process=False, client=client))
    duplicate_result = asyncio.run(GitHubService(db_session).sync(auto_process=False, client=client))

    assert result["imported_count"] == 3
    assert result["skipped_count"] == 0
    assert duplicate_result["imported_count"] == 0
    assert duplicate_result["skipped_count"] == 3
    assert db_session.query(RawItem).count() == 3
    issue = db_session.query(RawItem).filter(RawItem.source_uri == "github:owner/repo:issue:11").one()
    assert issue.source_type == "github"
    assert issue.title == "repo issue #11: Fix sync"
    assert "GitHub issue: Fix sync" in issue.body_text
    assert issue.metadata_json["github"]["repository"] == "owner/repo"
    workflow_run = db_session.query(RawItem).filter(RawItem.source_uri == "github:owner/repo:workflow_run:3001").one()
    assert workflow_run.title == "repo workflow failed: Tests"
    assert "GitHub workflow run failed: Tests" in workflow_run.body_text
    assert workflow_run.metadata_json["github"]["conclusion"] == "failure"


class FakeGitHubClient:
    def get_repo(self, repository: str) -> dict:
        return {"id": 123, "name": "repo", "full_name": repository}

    def list_repo_records(self, repository: str, collection: str, max_results: int) -> list[dict]:
        if collection == "issues":
            return [
                {
                    "id": 1011,
                    "number": 11,
                    "title": "Fix sync",
                    "body": "Sync drops labels.",
                    "state": "open",
                    "labels": [{"name": "bug"}],
                    "assignees": [{"login": "rmoore"}],
                    "user": {"login": "alex"},
                    "html_url": "https://github.com/owner/repo/issues/11",
                    "updated_at": "2026-06-22T12:00:00Z",
                },
                {
                    "id": 1012,
                    "number": 12,
                    "title": "PR masquerading as issue",
                    "pull_request": {},
                    "state": "open",
                    "labels": [],
                    "assignees": [],
                    "user": {"login": "alex"},
                    "html_url": "https://github.com/owner/repo/pull/12",
                    "updated_at": "2026-06-22T12:30:00Z",
                },
            ]
        return [
            {
                "id": 2004,
                "number": 4,
                "title": "Add sync button",
                "body": "Adds a sync button.",
                "state": "open",
                "labels": [{"name": "feature"}],
                "assignees": [],
                "user": {"login": "dev"},
                "html_url": "https://github.com/owner/repo/pull/4",
                "updated_at": "2026-06-22T13:00:00Z",
            }
        ]

    def list_workflow_runs(self, repository: str, max_results: int) -> list[dict]:
        return [
            {
                "id": 3001,
                "name": "Tests",
                "status": "completed",
                "conclusion": "failure",
                "head_branch": "main",
                "head_sha": "abc123",
                "html_url": "https://github.com/owner/repo/actions/runs/3001",
                "updated_at": "2026-06-22T14:00:00Z",
            },
            {
                "id": 3002,
                "name": "Lint",
                "status": "completed",
                "conclusion": "success",
                "head_branch": "main",
                "head_sha": "def456",
                "html_url": "https://github.com/owner/repo/actions/runs/3002",
                "updated_at": "2026-06-22T15:00:00Z",
            },
        ]
