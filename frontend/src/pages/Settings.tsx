import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save } from 'lucide-react';
import { getSettings, listOllamaModels, patchSettings } from '../api/views';

export default function Settings() {
  const [inboxFolder, setInboxFolder] = useState('');
  const [extractionModel, setExtractionModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [gmailEnabled, setGmailEnabled] = useState(false);
  const [gmailLabel, setGmailLabel] = useState('');
  const [gmailQuery, setGmailQuery] = useState('');
  const [gmailAutoProcess, setGmailAutoProcess] = useState(true);
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['settings'], queryFn: getSettings });
  const ollamaModels = useQuery({ queryKey: ['ollama-models'], queryFn: listOllamaModels, retry: false });
  const saveSettings = useMutation({
    mutationFn: () =>
      patchSettings({
        inbox_folder: inboxFolder,
        ollama_extraction_model: extractionModel,
        ollama_embedding_model: embeddingModel,
        gmail_enabled: gmailEnabled,
        gmail_label: gmailLabel,
        gmail_query: gmailQuery,
        gmail_auto_process: gmailAutoProcess
      }),
    onSuccess: (data) => {
      setInboxFolder(data.inbox_folder);
      setExtractionModel(data.ollama_extraction_model);
      setEmbeddingModel(data.ollama_embedding_model);
      setGmailEnabled(data.gmail_enabled);
      setGmailLabel(data.gmail_label);
      setGmailQuery(data.gmail_query);
      setGmailAutoProcess(data.gmail_auto_process);
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });

  useEffect(() => {
    if (settings.data) {
      setInboxFolder(settings.data.inbox_folder);
      setExtractionModel(settings.data.ollama_extraction_model);
      setEmbeddingModel(settings.data.ollama_embedding_model);
      setGmailEnabled(settings.data.gmail_enabled);
      setGmailLabel(settings.data.gmail_label);
      setGmailQuery(settings.data.gmail_query);
      setGmailAutoProcess(settings.data.gmail_auto_process);
    }
  }, [settings.data]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (inboxFolder.trim()) saveSettings.mutate();
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Settings</h1>
      {settings.data && (
        <div className="space-y-5">
          <dl className="grid gap-3 text-sm md:grid-cols-[220px_minmax(0,1fr)]">
            <dt className="font-medium text-slate-600">Ollama URL</dt>
            <dd>{settings.data.ollama_base_url}</dd>
            <dt className="font-medium text-slate-600">Extraction model</dt>
            <dd>{settings.data.ollama_extraction_model}</dd>
            <dt className="font-medium text-slate-600">Embedding model</dt>
            <dd>{settings.data.ollama_embedding_model}</dd>
            <dt className="font-medium text-slate-600">Gmail</dt>
            <dd>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{settings.data.gmail_status}</span>
            </dd>
            <dt className="font-medium text-slate-600">Gmail credentials</dt>
            <dd>
              {settings.data.gmail_credentials_path}
              <span className={`ml-2 rounded px-2 py-1 text-xs ${settings.data.gmail_credentials_exists ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {settings.data.gmail_credentials_exists ? 'found' : 'missing'}
              </span>
            </dd>
            <dt className="font-medium text-slate-600">Gmail token</dt>
            <dd>
              {settings.data.gmail_token_path}
              <span className={`ml-2 rounded px-2 py-1 text-xs ${settings.data.gmail_token_exists ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {settings.data.gmail_token_exists ? 'authorized' : 'needs auth'}
              </span>
            </dd>
            <dt className="font-medium text-slate-600">Latest Gmail sync</dt>
            <dd>
              {settings.data.gmail_last_sync
                ? `${settings.data.gmail_last_sync.status}: imported ${settings.data.gmail_last_sync.imported_count}, queued ${settings.data.gmail_last_sync.queued_count ?? 0}, skipped ${settings.data.gmail_last_sync.skipped_count}`
                : 'none'}
            </dd>
          </dl>
          <form onSubmit={submit} className="max-w-3xl space-y-2 border-t border-slate-200 pt-4">
            <label className="block text-sm font-medium text-slate-700">
              Inbox folder
              <input
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
                value={inboxFolder}
                onChange={(event) => setInboxFolder(event.target.value)}
              />
            </label>
            <div className="grid gap-3 border-t border-slate-200 pt-4 md:grid-cols-2">
              <label className="block text-sm font-medium text-slate-700">
                Extraction / Ask model
                {ollamaModels.data?.completion_models.length ? (
                  <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={extractionModel} onChange={(event) => setExtractionModel(event.target.value)}>
                    {ollamaModels.data.completion_models.map((model) => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                ) : (
                  <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={extractionModel} onChange={(event) => setExtractionModel(event.target.value)} />
                )}
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Embedding model
                {ollamaModels.data?.embedding_models.length ? (
                  <select className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={embeddingModel} onChange={(event) => setEmbeddingModel(event.target.value)}>
                    {ollamaModels.data.embedding_models.map((model) => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                ) : (
                  <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={embeddingModel} onChange={(event) => setEmbeddingModel(event.target.value)} />
                )}
              </label>
              <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-600 md:col-span-2">
                Recommended defaults: `qwen3:8b` for extraction and Ask, `nomic-embed-text` for embeddings. Use `llama3.1:8b` as a fallback completion model, smaller models for speed, and larger Qwen/Gemma/Mistral models when extraction quality matters more than latency.
              </div>
              {ollamaModels.error && <p className="text-sm text-amber-700 md:col-span-2">Could not list installed Ollama models. Manual model names are still accepted.</p>}
            </div>
            <div className="grid gap-3 border-t border-slate-200 pt-4 md:grid-cols-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={gmailEnabled} onChange={(event) => setGmailEnabled(event.target.checked)} />
                Gmail enabled
              </label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={gmailAutoProcess} onChange={(event) => setGmailAutoProcess(event.target.checked)} />
                Auto-process imported emails
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Gmail label
                <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={gmailLabel} onChange={(event) => setGmailLabel(event.target.value)} />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Gmail query
                <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={gmailQuery} onChange={(event) => setGmailQuery(event.target.value)} />
              </label>
            </div>
            <button
              disabled={saveSettings.isPending || !inboxFolder.trim() || !extractionModel.trim() || !embeddingModel.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              {saveSettings.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save
            </button>
            {saveSettings.error && <p className="text-sm text-red-700">{saveSettings.error.message}</p>}
          </form>
        </div>
      )}
    </section>
  );
}
