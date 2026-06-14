import { useEffect, useState } from 'react';
import { Loader2, Plus, Save, X } from 'lucide-react';
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
  const [ideas, setIdeas] = useState<EditableIdea[]>(() => memory.ideas.map((idea) => ({ id: idea.id, body: idea.body })));
  const [questions, setQuestions] = useState<EditableQuestion[]>(() =>
    memory.open_questions.map((question) => ({ id: question.id, question: question.question, status: question.status }))
  );

  useEffect(() => {
    setSummary(memory.summary);
    setTags(memory.tags.join(', '));
    setTasks(memory.tasks.map(toEditableTask));
    setIdeas(memory.ideas.map((idea) => ({ id: idea.id, body: idea.body })));
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
      <div className="grid gap-4 xl:grid-cols-3">
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
                    onChange={(event) => updateIdea(index, event.target.value)}
                    placeholder="Idea"
                  />
                  {idea.isNew && (
                    <button type="button" onClick={() => removeIdea(index)} className="rounded-md border border-slate-300 p-1.5 text-slate-600" title="Remove unsaved idea">
                      <X size={14} />
                    </button>
                  )}
                </div>
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

  function updateIdea(index: number, body: string) {
    setIdeas((current) => current.map((idea, ideaIndex) => (ideaIndex === index ? { ...idea, body } : idea)));
  }

  function addIdea() {
    setIdeas((current) => [{ id: tempId('idea'), isNew: true, body: '' }, ...current]);
  }

  function removeIdea(index: number) {
    setIdeas((current) => current.filter((_, ideaIndex) => ideaIndex !== index));
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

function tempId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
