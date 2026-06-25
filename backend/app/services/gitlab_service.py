import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RawItem
from app.services.processing_queue_service import ProcessingQueueService
from app.services.settings_service import SettingsService


class GitLabService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = SettingsService(db)

    async def sync(self, max_results: int = 20, auto_process: bool | None = None, client: Any | None = None) -> dict:
        if not self.settings.get_gitlab_enabled():
            raise RuntimeError("GitLab sync is disabled.")
        project_paths = self.settings.get_gitlab_project_paths()
        if not project_paths:
            raise RuntimeError("Add at least one GitLab project path.")
        if not self.settings.get_gitlab_token() and client is None:
            raise RuntimeError("GitLab token is not configured.")

        imported: list[RawItem] = []
        skipped: list[str] = []
        failures: list[dict] = []

        for project_path in project_paths:
            try:
                project = self._get_project(project_path, client=client)
                for item_type, records in (
                    ("issue", self._list_project_records(project_path, "issues", max_results, client=client)),
                    ("merge_request", self._list_project_records(project_path, "merge_requests", max_results, client=client)),
                ):
                    for record in records:
                        source_uri = self._source_uri(project_path, item_type, record)
                        if self._already_imported(source_uri):
                            skipped.append(source_uri)
                            continue
                        imported.append(self._import_record(project, project_path, item_type, record, source_uri))
            except Exception as exc:
                failures.append({"project_path": project_path, "error": str(exc)})

        should_process = self.settings.get_gitlab_auto_process() if auto_process is None else auto_process
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
            "base_url": self.settings.get_gitlab_base_url(),
            "project_paths": project_paths,
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
        self.settings.set_gitlab_last_sync_result({key: value for key, value in result.items() if key != "imported_items"})
        return result

    def _get_project(self, project_path: str, client: Any | None = None) -> dict:
        if client:
            return client.get_project(project_path)
        return self._request_json(f"/projects/{quote(project_path, safe='')}")

    def _list_project_records(self, project_path: str, collection: str, max_results: int, client: Any | None = None) -> list[dict]:
        if client:
            return client.list_project_records(project_path, collection, max_results)
        return self._request_json(
            f"/projects/{quote(project_path, safe='')}/{collection}",
            {"state": "opened", "order_by": "updated_at", "sort": "desc", "per_page": str(max_results)},
        )

    def _request_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        base_url = self.settings.get_gitlab_base_url().rstrip("/")
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{base_url}/api/v4{path}{query}",
            headers={
                "PRIVATE-TOKEN": self.settings.get_gitlab_token(),
                "Accept": "application/json",
                "User-Agent": "second-brain-inbox",
            },
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _already_imported(self, source_uri: str) -> bool:
        return self.db.scalar(select(RawItem).where(RawItem.source_uri == source_uri)) is not None

    def _import_record(self, project: dict, project_path: str, item_type: str, record: dict, source_uri: str) -> RawItem:
        title = self._title(project, item_type, record)
        raw_item = RawItem(
            source_type="gitlab",
            title=title[:200],
            body_text=self._body_text(project, project_path, item_type, record),
            content_type="application/vnd.gitlab+json",
            source_uri=source_uri,
            metadata_json={
                "gitlab": {
                    "item_type": item_type,
                    "project_id": project.get("id"),
                    "project_path": project_path,
                    "project_name": project.get("name") or project_path,
                    "iid": record.get("iid"),
                    "id": record.get("id"),
                    "state": record.get("state"),
                    "labels": record.get("labels") or [],
                    "web_url": record.get("web_url"),
                    "updated_at": record.get("updated_at"),
                }
            },
        )
        self.db.add(raw_item)
        self.db.commit()
        self.db.refresh(raw_item)
        return raw_item

    def _title(self, project: dict, item_type: str, record: dict) -> str:
        project_name = project.get("name") or project.get("path_with_namespace") or "GitLab"
        prefix = "MR" if item_type == "merge_request" else "issue"
        return f"{project_name} {prefix} #{record.get('iid')}: {record.get('title') or 'Untitled'}"

    def _body_text(self, project: dict, project_path: str, item_type: str, record: dict) -> str:
        labels = ", ".join(record.get("labels") or []) or "none"
        assignees = ", ".join((user.get("name") or user.get("username") or "unknown") for user in record.get("assignees") or []) or "none"
        author = (record.get("author") or {}).get("name") or (record.get("author") or {}).get("username") or "unknown"
        type_label = "merge request" if item_type == "merge_request" else "issue"
        lines = [
            f"GitLab {type_label}: {record.get('title') or 'Untitled'}",
            f"Project: {project.get('name') or project_path} ({project_path})",
            f"State: {record.get('state')}",
            f"Author: {author}",
            f"Assignees: {assignees}",
            f"Labels: {labels}",
            f"URL: {record.get('web_url') or ''}",
            "",
            record.get("description") or "",
        ]
        return "\n".join(lines).strip()

    def _source_uri(self, project_path: str, item_type: str, record: dict) -> str:
        return f"gitlab:{project_path}:{item_type}:{record.get('iid') or record.get('id')}"
