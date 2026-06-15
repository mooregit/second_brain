import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listOpenQuestions } from '../api/views';
import SourceLink from '../components/SourceLink';

export default function OpenQuestions() {
  const [showArchived, setShowArchived] = useState(false);
  const questions = useQuery({ queryKey: ['open-questions', showArchived], queryFn: () => listOpenQuestions(showArchived) });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Open Questions</h1>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} />
          Show archived
        </label>
      </div>
      <div className="divide-y divide-slate-100">
        {questions.data?.map((question) => (
          <article key={question.id} className="py-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-medium">{question.question}</h2>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs">{question.status}</span>
            </div>
            <div className="mt-2 text-sm"><SourceLink rawItemId={question.source_raw_item_id} label="Source" /></div>
          </article>
        ))}
      </div>
    </section>
  );
}
