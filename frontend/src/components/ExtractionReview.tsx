import { useEffect, useState } from 'react';
import { Archive, Loader2, Plus, Save, X } from 'lucide-react';
import type { Memory } from '../api/items';

type EditableTask = {
  id: string;
  isNew?: boolean;
  title: string;
  description: string;
  priority: string;
  status: string;
};

type EditableIdea = {
  id: string;
  isNew?: boolean;
  body: string;
  status: string;
};

type EditableDecision = {
  id: string;
  isNew?: boolean;
  title: string;
  rationale: string;
  confidence: number;
};

type EditableQuestion = {
  id: string;
  isNew?: boolean;
  question: string;
  status: string;
};

export type ExtractionReviewPayload = {
  summary: string;
  tags: string[];
  tasks: EditableTask[];
  ideas: EditableIdea[];
  decisions: EditableDecision[];
  open_questions: EditableQuestion[];
};

export default function ExtractionReview({
  memory,
  isSaving,
  onSave
}: {
  memory: Memory;
  isSaving: boolean;
  onSave: (payload: ExtractionReviewPayload) => void;
}) {
  const [summary, setSummary] = useState(memory.summary);
  const [tags, setTags] = useState(memory.tags.join(', '));
  const [tasks, setTasks] = useState<EditableTask[]>(() => memory.tasks.map(toEditableTask));
  const [ideas, setIdeas] = useState<EditableIdea[]>(() => memory.ideas.map(toEditableIdea));
  const [decisions, setDecisions] = useState<EditableDecision[]>(() => memory.decisions.map(toEditableDecision));
  const [questions, setQuestions] = useState<EditableQuestion[]>(() =>
    memory.open_questions.map((question) => ({ id: question.id, question: question.question, status: question.status }))
  );

  useEffect(() => {
    setSummary(memory.summary);
    setTags(memory.tags.join(', '));
    setTasks(memory.tasks.map(toEditableTask));
    setIdeas(memory.ideas.map(toEditableIdea));
    setDecisions(memory.decisions.map(toEditableDecision));
    setQuestions(memory.open_questions.map((question) => ({ id: question.id, question: question.question, status: question.status })));
  }, [memory]);

  function save() {
    onSave({
      summary,
      tags: tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      tasks,
      ideas,
      decisions,
      open_questions: questions
    });
  }

  return (
    <section className="space-y-4 border-t border-slate-200 pt-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Review</h2>
        <button
          onClick={save}
          disabled={isSaving}
          className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          title="Save extraction edits"
        >
          {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {isSaving ? 'Saving' : 'Save'}
        </button>
      </div>
      <label className="block text-sm font-medium text-slate-700">
        Summary
        <textarea className="mt-1 h-24 w-full rounded-md border border-slate-300 bg-white p-3" value={summary} onChange={(event) => setSummary(event.target.value)} />
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Tags
        <input className="mt-1 w-full rounded-md border border-slate-300 bg-white p-2" value={tags} onChange={(event) => setTags(event.target.value)} />
      </label>
      <div className="grid gap-4 xl:grid-cols-2 2xl:grid-cols-4">
        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Tasks</h3>
            <button type="button" onClick={addTask} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700" title="Add task">
              <Plus size={14} />
              Add
            </button>
          </div>
          <ul className="space-y-2">
            {tasks.map((task, index) => (
              <li key={task.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-start gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1 font-medium"
                    value={task.title}
                    onChange={(event) => updateTask(index, { title: event.target.value })}
                    placeholder="Task title"
                  />
                  {task.isNew && (
                    <button type="button" onClick={() => removeTask(index)} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Remove unsaved task">
                      <X size={14} />
                    </button>
                  )}
                  {!task.isNew && task.status !== 'archived' && (
                    <button type="button" onClick={() => updateTask(index, { status: 'archived' })} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Archive task">
                      <Archive size={14} />
                    </button>
                  )}
                </div>
                <textarea
                  className="h-20 w-full rounded-md border border-slate-300 px-2 py-1"
                  value={task.description}
                  onChange={(event) => updateTask(index, { description: event.target.value })}
                  placeholder="Description"
                />
                <div className="grid grid-cols-2 gap-2">
                  <select className="rounded-md border border-slate-300 px-2 py-1" value={task.status} onChange={(event) => updateTask(index, { status: event.target.value })}>
                    <option value="open">Open</option>
                    <option value="in_progress">In progress</option>
                    <option value="done">Done</option>
                    <option value="archived">Archived</option>
                  </select>
                  <select className="rounded-md border border-slate-300 px-2 py-1" value={task.priority} onChange={(event) => updateTask(index, { priority: event.target.value })}>
                    <option value="">No priority</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Ideas</h3>
            <button type="button" onClick={addIdea} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700" title="Add idea">
              <Plus size={14} />
              Add
            </button>
          </div>
          <ul className="space-y-2">
            {ideas.map((idea, index) => (
              <li key={idea.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-start gap-2">
                  <textarea
                    className="h-28 min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
                    value={idea.body}
                    onChange={(event) => updateIdea(index, { body: event.target.value })}
                    placeholder="Idea"
                  />
                  {idea.isNew && (
                    <button type="button" onClick={() => removeIdea(index)} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Remove unsaved idea">
                      <X size={14} />
                    </button>
                  )}
                  {!idea.isNew && idea.status !== 'archived' && (
                    <button type="button" onClick={() => updateIdea(index, { status: 'archived' })} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Archive idea">
                      <Archive size={14} />
                    </button>
                  )}
                </div>
                <select className="w-full rounded-md border border-slate-300 px-2 py-1" value={idea.status} onChange={(event) => updateIdea(index, { status: event.target.value })}>
                  <option value="active">Active</option>
                  <option value="archived">Archived</option>
                </select>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Decisions</h3>
            <button type="button" onClick={addDecision} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700" title="Add decision">
              <Plus size={14} />
              Add
            </button>
          </div>
          <ul className="space-y-2">
            {decisions.map((decision, index) => (
              <li key={decision.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-start gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1 font-medium"
                    value={decision.title}
                    onChange={(event) => updateDecision(index, { title: event.target.value })}
                    placeholder="Decision title"
                  />
                  {decision.isNew && (
                    <button type="button" onClick={() => removeDecision(index)} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Remove unsaved decision">
                      <X size={14} />
                    </button>
                  )}
                </div>
                <textarea
                  className="h-24 w-full rounded-md border border-slate-300 px-2 py-1"
                  value={decision.rationale}
                  onChange={(event) => updateDecision(index, { rationale: event.target.value })}
                  placeholder="Rationale"
                />
                <label className="block text-xs font-medium text-slate-600">
                  Confidence
                  <input
                    className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1"
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={decision.confidence}
                    onChange={(event) => updateDecision(index, { confidence: Number(event.target.value) })}
                  />
                </label>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Open Questions</h3>
            <button type="button" onClick={addQuestion} className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700" title="Add open question">
              <Plus size={14} />
              Add
            </button>
          </div>
          <ul className="space-y-2">
            {questions.map((question, index) => (
              <li key={question.id} className="space-y-2 rounded-md border border-slate-200 bg-white p-3 text-sm">
                <div className="flex items-start gap-2">
                  <textarea
                    className="h-24 min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1"
                    value={question.question}
                    onChange={(event) => updateQuestion(index, { question: event.target.value })}
                    placeholder="Open question"
                  />
                  {question.isNew && (
                    <button type="button" onClick={() => removeQuestion(index)} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Remove unsaved question">
                      <X size={14} />
                    </button>
                  )}
                  {!question.isNew && question.status !== 'archived' && (
                    <button type="button" onClick={() => updateQuestion(index, { status: 'archived' })} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Archive open question">
                      <Archive size={14} />
                    </button>
                  )}
                </div>
                <select className="w-full rounded-md border border-slate-300 px-2 py-1" value={question.status} onChange={(event) => updateQuestion(index, { status: event.target.value })}>
                  <option value="open">Open</option>
                  <option value="answered">Answered</option>
                  <option value="archived">Archived</option>
                </select>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );

  function updateTask(index: number, patch: Partial<EditableTask>) {
    setTasks((current) => current.map((task, taskIndex) => (taskIndex === index ? { ...task, ...patch } : task)));
  }

  function addTask() {
    setTasks((current) => [{ id: tempId('task'), isNew: true, title: '', description: '', priority: '', status: 'open' }, ...current]);
  }

  function removeTask(index: number) {
    setTasks((current) => current.filter((_, taskIndex) => taskIndex !== index));
  }

  function updateIdea(index: number, patch: Partial<EditableIdea>) {
    setIdeas((current) => current.map((idea, ideaIndex) => (ideaIndex === index ? { ...idea, ...patch } : idea)));
  }

  function addIdea() {
    setIdeas((current) => [{ id: tempId('idea'), isNew: true, body: '', status: 'active' }, ...current]);
  }

  function removeIdea(index: number) {
    setIdeas((current) => current.filter((_, ideaIndex) => ideaIndex !== index));
  }

  function updateDecision(index: number, patch: Partial<EditableDecision>) {
    setDecisions((current) => current.map((decision, decisionIndex) => (decisionIndex === index ? { ...decision, ...patch } : decision)));
  }

  function addDecision() {
    setDecisions((current) => [{ id: tempId('decision'), isNew: true, title: '', rationale: '', confidence: 0.5 }, ...current]);
  }

  function removeDecision(index: number) {
    setDecisions((current) => current.filter((_, decisionIndex) => decisionIndex !== index));
  }

  function updateQuestion(index: number, patch: Partial<EditableQuestion>) {
    setQuestions((current) => current.map((question, questionIndex) => (questionIndex === index ? { ...question, ...patch } : question)));
  }

  function addQuestion() {
    setQuestions((current) => [{ id: tempId('question'), isNew: true, question: '', status: 'open' }, ...current]);
  }

  function removeQuestion(index: number) {
    setQuestions((current) => current.filter((_, questionIndex) => questionIndex !== index));
  }
}

function toEditableTask(task: Memory['tasks'][number]): EditableTask {
  return {
    id: task.id,
    title: task.title,
    description: task.description ?? '',
    priority: task.priority ?? '',
    status: task.status
  };
}

function toEditableIdea(idea: Memory['ideas'][number]): EditableIdea {
  return {
    id: idea.id,
    body: idea.body,
    status: idea.status
  };
}

function toEditableDecision(decision: Memory['decisions'][number]): EditableDecision {
  return {
    id: decision.id,
    title: decision.title,
    rationale: decision.rationale ?? '',
    confidence: decision.confidence
  };
}

function tempId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
