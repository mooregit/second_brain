import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send } from 'lucide-react';
import { askQuestion } from '../api/ask';
import SourceLink from '../components/SourceLink';

export default function Ask() {
  const [question, setQuestion] = useState('');
  const ask = useMutation({ mutationFn: () => askQuestion(question) });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim()) ask.mutate();
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
          />
          <button className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white" disabled={ask.isPending}>
            <Send size={16} />
            Ask
          </button>
        </form>
        {ask.data && <div className="mt-5 whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm leading-6">{ask.data.answer}</div>}
        {ask.error && <p className="mt-3 text-sm text-red-700">{ask.error.message}</p>}
      </section>
      <aside className="rounded-md border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-base font-semibold">Sources</h2>
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

