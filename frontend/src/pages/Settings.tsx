import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Save } from 'lucide-react';
import { getSettings, patchSettings } from '../api/views';

export default function Settings() {
  const [inboxFolder, setInboxFolder] = useState('');
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['settings'], queryFn: getSettings });
  const saveSettings = useMutation({
    mutationFn: () => patchSettings({ inbox_folder: inboxFolder }),
    onSuccess: (data) => {
      setInboxFolder(data.inbox_folder);
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });

  useEffect(() => {
    if (settings.data) setInboxFolder(settings.data.inbox_folder);
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
            <dd>{settings.data.gmail_status}</dd>
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
            <button
              disabled={saveSettings.isPending || !inboxFolder.trim()}
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
