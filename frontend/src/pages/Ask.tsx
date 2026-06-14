import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Check, Loader2, Save, Send } from 'lucide-react';
import { askQuestion, saveAskResult, type AskSavePayload } from '../api/ask';
import SourceLink from '../components/SourceLink';

type SaveMode = 'task' | 'open_question' | 'decision';

export default function Ask() {
  const [question, setQuestion] = useState('');
  const [saveMode, setSaveMode] = useState<SaveMode>('open_question');
  const [saveTitle, setSaveTitle] = useState('');
  const [saveBody, setSaveBody] = useState('');
  const [confidence, setConfidence] = useState(0.7);
  const ask = useMutation({
    mutationFn: () => askQuestion(question),
    onSuccess: (data) => {
      setSaveTitle(question);
      setSaveBody(data.answer);
      setSaveMode('open_question');
    }
  });
  const save = useMutation({
    mutationFn: (payload: AskSavePayload) => {
      if (!ask.data?.ask_run_id) throw new Error('Ask result is missing a history id.');
      return saveAskResult(ask.data.ask_run_id, payload);
    }
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim()) ask.mutate();
  }

  function saveResult() {
    const title = saveTitle.trim();
    const body = saveBody.trim();
    save.mutate({
      save_as: saveMode,
      title,
      body,
      rationale: saveMode === 'decision' ? body : undefined,
      confidence: saveMode === 'decision' ? confidence : undefined
    });
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <h1 className="mb-3 text-xl font-semibold">Ask</h1>
        <form onSubmit={submit} className="flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What are my open BetRight tasks?"
            disabled={ask.isPending}
          />
          <button className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white" disabled={ask.isPending}>
            {ask.isPending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            {ask.isPending ? 'Asking' : 'Ask'}
          </button>
        </form>
        {ask.isPending && (
          <div className="mt-5 flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <Loader2 size={16} className="animate-spin" />
            Searching memories and asking the local model.
          </div>
        )}
        {ask.data && <div className="mt-5 whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm leading-6">{ask.data.answer}</div>}
        {ask.data?.ask_run_id && (
          <div className="mt-4 space-y-3 rounded-md border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-slate-700">Save Result</h2>
              <div className="flex rounded-md border border-slate-300 p-1 text-xs">
                <ModeButton active={saveMode === 'open_question'} onClick={() => setSaveMode('open_question')} label="Open Question" />
                <ModeButton active={saveMode === 'decision'} onClick={() => setSaveMode('decision')} label="Decision" />
                <ModeButton active={saveMode === 'task'} onClick={() => setSaveMode('task')} label="Task" />
              </div>
            </div>
            <input
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={saveTitle}
              onChange={(event) => setSaveTitle(event.target.value)}
              placeholder={saveMode === 'task' ? 'Task title' : saveMode === 'decision' ? 'Decision title' : 'Open question'}
            />
            <textarea
              className="h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={saveBody}
              onChange={(event) => setSaveBody(event.target.value)}
              placeholder={saveMode === 'decision' ? 'Rationale' : saveMode === 'task' ? 'Description' : 'Context'}
            />
            {saveMode === 'decision' && (
              <label className="block text-xs font-medium text-slate-600">
                Confidence
                <input
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={confidence}
                  onChange={(event) => setConfidence(Number(event.target.value))}
                />
              </label>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={saveResult}
                disabled={save.isPending || !saveTitle.trim()}
                className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
              >
                {save.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {save.isPending ? 'Saving' : 'Save'}
              </button>
              {save.data && (
                <div className="inline-flex items-center gap-1 text-sm text-emerald-700">
                  <Check size={16} />
                  Saved as {save.data.entity_type.replace('_', ' ')}
                </div>
              )}
              {save.error && <p className="text-sm text-red-700">{save.error.message}</p>}
            </div>
          </div>
        )}
        {ask.error && <p className="mt-3 text-sm text-red-700">{ask.error.message}</p>}
      </section>
      <aside className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-base font-semibold">Sources</h2>
        {ask.isPending && <div className="text-sm text-slate-500">Waiting for retrieved sources...</div>}
        <ul className="space-y-3">
          {ask.data?.sources.map((source) => (
            <li key={`${source.owner_type}:${source.owner_id}`} className="text-sm">
              <SourceLink rawItemId={source.raw_item_id} label={source.title} />
              <div className="text-xs text-slate-500">{source.owner_type} · {source.score.toFixed(3)}</div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}

function ModeButton({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded px-2 py-1 ${active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
    >
      {label}
    </button>
  );
}
