from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Decision, Idea, OpenQuestion, Project, RawItem, Task


class ProjectBriefService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(self, project: Project) -> dict:
        tasks = sorted(project.tasks, key=lambda task: task.created_at, reverse=True)
        ideas = sorted(project.ideas, key=lambda idea: idea.created_at, reverse=True)
        decisions = sorted(project.decisions, key=lambda decision: decision.created_at, reverse=True)
        questions = sorted(project.open_questions, key=lambda question: question.created_at, reverse=True)

        open_tasks = [task for task in tasks if task.status != "archived"]
        active_ideas = [idea for idea in ideas if idea.status != "archived"]
        open_questions = [question for question in questions if question.status not in {"archived", "answered"}]
        answered_questions = [question for question in questions if question.status == "answered"]
        github_failures = self._github_failures(project)
        risks = self._risks(open_tasks, active_ideas, decisions, open_questions, github_failures)
        next_actions = self._next_actions(open_tasks, active_ideas, decisions, open_questions, github_failures)

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at.isoformat(),
            },
            "summary": self._summary(project, open_tasks, active_ideas, decisions, open_questions, risks),
            "counts": {
                "open_tasks": len(open_tasks),
                "active_ideas": len(active_ideas),
                "decisions": len(decisions),
                "open_questions": len(open_questions),
                "answered_questions": len(answered_questions),
            },
            "risks": risks,
            "next_actions": next_actions,
            "github_failures": github_failures,
            "recent_sources": self._recent_sources([*open_tasks, *active_ideas, *decisions, *open_questions])[:6],
            "open_tasks": [self._task_dict(task) for task in open_tasks[:8]],
            "open_questions": [self._question_dict(question) for question in open_questions[:8]],
            "active_ideas": [self._idea_dict(idea) for idea in active_ideas[:8]],
            "recent_decisions": [self._decision_dict(decision) for decision in decisions[:8]],
        }

    def _summary(
        self,
        project: Project,
        open_tasks: list[Task],
        active_ideas: list[Idea],
        decisions: list[Decision],
        open_questions: list[OpenQuestion],
        risks: list[str],
    ) -> str:
        parts = [
            f"{project.name} has {len(open_tasks)} open task{'s' if len(open_tasks) != 1 else ''}",
            f"{len(open_questions)} open question{'s' if len(open_questions) != 1 else ''}",
            f"{len(active_ideas)} active idea{'s' if len(active_ideas) != 1 else ''}",
            f"and {len(decisions)} decision{'s' if len(decisions) != 1 else ''}.",
        ]
        if risks:
            parts.append(f"Main flag: {risks[0].replace('_', ' ')}.")
        elif open_tasks:
            parts.append(f"Next visible task: {open_tasks[0].title}.")
        else:
            parts.append("No immediate graph issues were detected.")
        return " ".join(parts)

    def _risks(self, open_tasks: list[Task], active_ideas: list[Idea], decisions: list[Decision], open_questions: list[OpenQuestion], github_failures: list[dict]) -> list[str]:
        risks = []
        if github_failures:
            risks.append("github_actions_failures")
        if open_questions and not decisions:
            risks.append("questions_without_decisions")
        if active_ideas and not open_tasks:
            risks.append("ideas_without_tasks")
        if not open_tasks and not active_ideas and not open_questions and not decisions:
            risks.append("empty_project")
        high_priority_tasks = [task for task in open_tasks if task.priority == "high"]
        if high_priority_tasks:
            risks.append("high_priority_open_tasks")
        return risks

    def _next_actions(self, open_tasks: list[Task], active_ideas: list[Idea], decisions: list[Decision], open_questions: list[OpenQuestion], github_failures: list[dict]) -> list[str]:
        actions = []
        if github_failures:
            actions.append(f"Investigate failing GitHub Actions workflow: {github_failures[0]['name']}")
        if open_questions and not decisions:
            actions.append(f"Resolve or decide the open question: {open_questions[0].question}")
        if active_ideas and not open_tasks:
            actions.append(f"Turn the strongest idea into a task: {active_ideas[0].body[:120]}")
        if open_tasks:
            actions.append(f"Work the next open task: {open_tasks[0].title}")
        if open_questions:
            actions.append(f"Answer the open question: {open_questions[0].question}")
        if not actions:
            actions.append("Capture the next task, question, or decision for this project.")
        return actions[:4]

    def _github_failures(self, project: Project) -> list[dict]:
        project_key = self._normalize(project.name)
        failures = []
        for raw_item in self.db.scalars(select(RawItem).where(RawItem.source_type == "github")).all():
            metadata = raw_item.metadata_json if isinstance(raw_item.metadata_json, dict) else {}
            github = metadata.get("github") if isinstance(metadata.get("github"), dict) else {}
            if github.get("item_type") != "workflow_run":
                continue
            if github.get("conclusion") not in {"failure", "timed_out", "cancelled", "action_required"}:
                continue
            repository = str(github.get("repository") or "")
            repo_name = repository.rsplit("/", 1)[-1]
            if project_key not in {self._normalize(repository), self._normalize(repo_name)}:
                continue
            failures.append(
                {
                    "raw_item_id": raw_item.id,
                    "name": github.get("name") or raw_item.title,
                    "repository": repository,
                    "conclusion": github.get("conclusion"),
                    "branch": github.get("head_branch"),
                    "url": github.get("html_url"),
                    "source_title": raw_item.title,
                }
            )
        return failures[:6]

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().replace("_", "-").split()).strip()

    def _recent_sources(self, records: list) -> list[dict]:
        raw_item_ids = []
        for record in records:
            raw_item_id = getattr(record, "source_raw_item_id", None)
            if raw_item_id and raw_item_id not in raw_item_ids:
                raw_item_ids.append(raw_item_id)
        raw_items = [self.db.get(RawItem, raw_item_id) for raw_item_id in raw_item_ids]
        return [
            {
                "raw_item_id": raw_item.id,
                "title": raw_item.title,
                "source_type": raw_item.source_type,
                "created_at": raw_item.created_at.isoformat(),
            }
            for raw_item in sorted([item for item in raw_items if item], key=lambda item: item.created_at, reverse=True)
        ]

    def _task_dict(self, task: Task) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "source_raw_item_id": task.source_raw_item_id,
        }

    def _idea_dict(self, idea: Idea) -> dict:
        return {
            "id": idea.id,
            "body": idea.body,
            "status": idea.status,
            "source_raw_item_id": idea.source_raw_item_id,
        }

    def _decision_dict(self, decision: Decision) -> dict:
        return {
            "id": decision.id,
            "title": decision.title,
            "rationale": decision.rationale,
            "confidence": decision.confidence,
            "source_raw_item_id": decision.source_raw_item_id,
        }

    def _question_dict(self, question: OpenQuestion) -> dict:
        return {
            "id": question.id,
            "question": question.question,
            "status": question.status,
            "answer_text": question.answer_text,
            "source_raw_item_id": question.source_raw_item_id,
        }
