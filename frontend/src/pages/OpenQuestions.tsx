import { useQuery } from '@tanstack/react-query';
import { listOpenQuestions } from '../api/views';
import SourceLink from '../components/SourceLink';

export default function OpenQuestions() {
  const questions = useQuery({ queryKey: ['open-questions'], queryFn: listOpenQuestions });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Open Questions</h1>
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
