import { useState } from 'react';
import { Save } from 'lucide-react';
import type { Memory } from '../api/items';

export default function ExtractionReview({
  memory,
  onSave
}: {
  memory: Memory;
  onSave: (payload: { summary: string; tags: string[] }) => void;
}) {
  const [summary, setSummary] = useState(memory.summary);
  const [tags, setTags] = useState(memory.tags.join(', '));

  return (
    <section className="space-y-4 border-t border-slate-200 pt-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Review</h2>
        <button
          onClick={() => onSave({ summary, tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean) })}
          className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white"
          title="Save memory edits"
        >
          <Save size={16} />
          Save
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
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <h3 className="mb-2 text-sm font-semibold">Tasks</h3>
          <ul className="space-y-2">
            {memory.tasks.map((task) => (
              <li key={task.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                <div className="font-medium">{task.title}</div>
                <div className="text-slate-500">{task.status}</div>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Ideas</h3>
          <ul className="space-y-2">
            {memory.ideas.map((idea) => (
              <li key={idea.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">{idea.body}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Open Questions</h3>
          <ul className="space-y-2">
            {memory.open_questions.map((question) => (
              <li key={question.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">{question.question}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

