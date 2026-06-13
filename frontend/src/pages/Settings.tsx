import { useQuery } from '@tanstack/react-query';
import { getSettings } from '../api/views';

export default function Settings() {
  const settings = useQuery({ queryKey: ['settings'], queryFn: getSettings });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Settings</h1>
      {settings.data && (
        <dl className="grid gap-3 text-sm md:grid-cols-[220px_minmax(0,1fr)]">
          <dt className="font-medium text-slate-600">Ollama URL</dt>
          <dd>{settings.data.ollama_base_url}</dd>
          <dt className="font-medium text-slate-600">Extraction model</dt>
          <dd>{settings.data.ollama_extraction_model}</dd>
          <dt className="font-medium text-slate-600">Embedding model</dt>
          <dd>{settings.data.ollama_embedding_model}</dd>
          <dt className="font-medium text-slate-600">Inbox folder</dt>
          <dd>{settings.data.inbox_folder}</dd>
          <dt className="font-medium text-slate-600">Gmail</dt>
          <dd>{settings.data.gmail_status}</dd>
        </dl>
      )}
    </section>
  );
}
