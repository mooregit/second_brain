import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RawItem
from app.services.processing_queue_service import ProcessingQueueService
from app.services.settings_service import SettingsService


class GitHubService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = SettingsService(db)

    async def sync(self, max_results: int = 20, auto_process: bool | None = None, client: Any | None = None) -> dict:
        if not self.settings.get_github_enabled():
            raise RuntimeError("GitHub sync is disabled.")
        repositories = self.settings.get_github_repository_names()
        if not repositories:
            raise RuntimeError("Add at least one GitHub repository.")
        if not self.settings.get_github_token() and client is None:
            raise RuntimeError("GitHub token is not configured.")

        imported: list[RawItem] = []
        skipped: list[str] = []
        failures: list[dict] = []

        for repository in repositories:
            try:
                repo = self._get_repo(repository, client=client)
                issue_records = [issue for issue in self._list_repo_records(repository, "issues", max_results, client=client) if "pull_request" not in issue]
                pull_records = self._list_repo_records(repository, "pulls", max_results, client=client)
                failed_workflow_records = [
                    run
                    for run in self._list_workflow_runs(repository, max_results, client=client)
                    if run.get("conclusion") in {"failure", "timed_out", "cancelled", "action_required"}
                ]
                for item_type, records in (("issue", issue_records), ("pull_request", pull_records), ("workflow_run", failed_workflow_records)):
                    for record in records:
                        source_uri = self._source_uri(repository, item_type, record)
                        if self._already_imported(source_uri):
                            skipped.append(source_uri)
                            continue
                        imported.append(self._import_record(repo, repository, item_type, record, source_uri))
            except Exception as exc:
                failures.append({"repository": repository, "error": str(exc)})

        should_process = self.settings.get_github_auto_process() if auto_process is None else auto_process
        queued: list[str] = []
        queued_runs: list[str] = []
        if should_process:
            for item in imported:
                try:
                    run = ProcessingQueueService(self.db).enqueue_item(item.id)
                    queued.append(item.id)
                    queued_runs.append(run.id)
                except Exception as exc:
                    failures.append({"raw_item_id": item.id, "error": str(exc)})

        result = {
            "status": "succeeded" if not failures else "completed_with_failures",
            "repositories": repositories,
            "auto_process": should_process,
            "max_results": max_results,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "imported_count": len(imported),
            "skipped_count": len(skipped),
            "queued_count": len(queued),
            "failed_count": len(failures),
            "imported_items": imported,
            "skipped_source_uris": skipped,
            "queued_item_ids": queued,
            "queued_run_ids": queued_runs,
            "failures": failures,
        }
        self.settings.set_github_last_sync_result({key: value for key, value in result.items() if key != "imported_items"})
        return result

    def _get_repo(self, repository: str, client: Any | None = None) -> dict:
        if client:
            return client.get_repo(repository)
        return self._request_json(f"/repos/{repository}")

    def _list_repo_records(self, repository: str, collection: str, max_results: int, client: Any | None = None) -> list[dict]:
        if client:
            return client.list_repo_records(repository, collection, max_results)
        return self._request_json(
            f"/repos/{repository}/{collection}",
            {"state": "open", "sort": "updated", "direction": "desc", "per_page": str(max_results)},
        )

    def _list_workflow_runs(self, repository: str, max_results: int, client: Any | None = None) -> list[dict]:
        if client:
            return client.list_workflow_runs(repository, max_results)
        response = self._request_json(
            f"/repos/{repository}/actions/runs",
            {"status": "completed", "per_page": str(max_results)},
        )
        return response.get("workflow_runs", []) if isinstance(response, dict) else []

    def _request_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"https://api.github.com{path}{query}",
            headers={
                "Authorization": f"Bearer {self.settings.get_github_token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "second-brain-inbox",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _already_imported(self, source_uri: str) -> bool:
        return self.db.scalar(select(RawItem).where(RawItem.source_uri == source_uri)) is not None

    def _import_record(self, repo: dict, repository: str, item_type: str, record: dict, source_uri: str) -> RawItem:
        title = self._title(repo, item_type, record)
        raw_item = RawItem(
            source_type="github",
            title=title[:200],
            body_text=self._body_text(repo, repository, item_type, record),
            content_type="application/vnd.github+json",
            source_uri=source_uri,
            metadata_json={
                "github": {
                    "item_type": item_type,
                    "repository": repository,
                    "repo_id": repo.get("id"),
                    "number": record.get("number"),
                    "id": record.get("id"),
                    "state": record.get("state"),
                    "name": record.get("name"),
                    "conclusion": record.get("conclusion"),
                    "head_branch": record.get("head_branch"),
                    "labels": [label.get("name") for label in record.get("labels") or [] if label.get("name")],
                    "html_url": record.get("html_url"),
                    "updated_at": record.get("updated_at"),
                }
            },
        )
        self.db.add(raw_item)
        self.db.commit()
        self.db.refresh(raw_item)
        return raw_item

    def _title(self, repo: dict, item_type: str, record: dict) -> str:
        repo_name = repo.get("name") or repo.get("full_name") or "GitHub"
        if item_type == "workflow_run":
            return f"{repo_name} workflow failed: {record.get('name') or 'Unnamed workflow'}"
        prefix = "PR" if item_type == "pull_request" else "issue"
        return f"{repo_name} {prefix} #{record.get('number')}: {record.get('title') or 'Untitled'}"

    def _body_text(self, repo: dict, repository: str, item_type: str, record: dict) -> str:
        labels = ", ".join(label.get("name") for label in record.get("labels") or [] if label.get("name")) or "none"
        assignees = ", ".join((user.get("login") or "unknown") for user in record.get("assignees") or []) or "none"
        author = (record.get("user") or {}).get("login") or "unknown"
        if item_type == "workflow_run":
            lines = [
                f"GitHub workflow run failed: {record.get('name') or 'Unnamed workflow'}",
                f"Repository: {repo.get('full_name') or repository}",
                f"Conclusion: {record.get('conclusion')}",
                f"Status: {record.get('status')}",
                f"Branch: {record.get('head_branch') or ''}",
                f"Commit: {record.get('head_sha') or ''}",
                f"URL: {record.get('html_url') or ''}",
                "",
                "Suggested action: investigate the failing GitHub Actions workflow and create or link a task if it blocks project progress.",
            ]
            return "\n".join(lines).strip()
        type_label = "pull request" if item_type == "pull_request" else "issue"
        lines = [
            f"GitHub {type_label}: {record.get('title') or 'Untitled'}",
            f"Repository: {repo.get('full_name') or repository}",
            f"State: {record.get('state')}",
            f"Author: {author}",
            f"Assignees: {assignees}",
            f"Labels: {labels}",
            f"URL: {record.get('html_url') or ''}",
            "",
            record.get("body") or "",
        ]
        return "\n".join(lines).strip()

    def _source_uri(self, repository: str, item_type: str, record: dict) -> str:
        return f"github:{repository}:{item_type}:{record.get('number') or record.get('id') or record.get('run_number')}"
