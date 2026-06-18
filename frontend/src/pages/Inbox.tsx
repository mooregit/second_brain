import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { FolderSync, Inbox as InboxIcon, Loader2, Plus, Trash2, Upload } from 'lucide-react';
import { createManualItem, deleteItem, listItems, scanInboxFolder, uploadItem } from '../api/items';
import { syncGmail } from '../api/gmail';

export default function Inbox() {
  const [note, setNote] = useState('');
  const queryClient = useQueryClient();
  const items = useQuery({ queryKey: ['items'], queryFn: listItems });
  const createMutation = useMutation({
    mutationFn: () => createManualItem(note),
    onSuccess: () => {
      setNote('');
      queryClient.invalidateQueries({ queryKey: ['items'] });
    }
  });
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadItem(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] })
  });
  const scanMutation = useMutation({
    mutationFn: scanInboxFolder,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] })
  });
  const gmailMutation = useMutation({
    mutationFn: () => syncGmail(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['items'] })
  });
  const deleteMutation = useMutation({
    mutationFn: deleteItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    }
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (note.trim()) createMutation.mutate();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Inbox</h1>
          <span className="text-sm text-slate-500">{items.data?.length ?? 0} items</span>
        </div>
        <div className="divide-y divide-slate-100">
          {items.data?.map((item) => (
            <Link key={item.id} to={`/items/${item.id}`} className="block py-3 hover:bg-slate-50">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium">{item.title}</div>
                  <div className="line-clamp-1 text-sm text-slate-500">{item.body_text}</div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{item.status}</span>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      if (window.confirm(`Delete inbox item "${item.title}" and all extracted records?`)) {
                        deleteMutation.mutate(item.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                    className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                    title="Delete inbox item"
                    aria-label={`Delete ${item.title}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </Link>
          ))}
          {items.data?.length === 0 && <div className="py-8 text-sm text-slate-500">No notes yet.</div>}
        </div>
      </section>
      <div className="space-y-4">
        <form onSubmit={submit} className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-base font-semibold">Manual Note</h2>
          <textarea
            className="h-64 w-full rounded-md border border-slate-300 p-3 text-sm"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Paste a note..."
          />
          <button
            disabled={createMutation.isPending || !note.trim()}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            {createMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            Add Note
          </button>
          {createMutation.error && <p className="mt-2 text-sm text-red-700">{createMutation.error.message}</p>}
        </form>
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-base font-semibold">File Inputs</h2>
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50">
            {uploadMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            Upload .txt or .md
            <input
              type="file"
              className="hidden"
              accept=".txt,.md,text/plain,text/markdown"
              disabled={uploadMutation.isPending}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) uploadMutation.mutate(file);
                event.currentTarget.value = '';
              }}
            />
          </label>
          <button
            type="button"
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
            className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50"
          >
            {scanMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <FolderSync size={16} />}
            Scan inbox folder
          </button>
          {scanMutation.data && (
            <p className="mt-2 text-sm text-slate-600">
              Imported {scanMutation.data.created_count}; skipped {scanMutation.data.skipped_count} from {scanMutation.data.folder}
            </p>
          )}
          {uploadMutation.error && <p className="mt-2 text-sm text-red-700">{uploadMutation.error.message}</p>}
          {scanMutation.error && <p className="mt-2 text-sm text-red-700">{scanMutation.error.message}</p>}
        </section>
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-base font-semibold">Gmail</h2>
          <button
            type="button"
            onClick={() => gmailMutation.mutate()}
            disabled={gmailMutation.isPending}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50"
          >
            {gmailMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <InboxIcon size={16} />}
            Sync Gmail
          </button>
          {gmailMutation.data && (
            <p className="mt-2 text-sm text-slate-600">
              Imported {gmailMutation.data.imported_count}; processed {gmailMutation.data.processed_count}; skipped {gmailMutation.data.skipped_count}
            </p>
          )}
          {gmailMutation.data?.failed_count ? <p className="mt-2 text-sm text-red-700">{gmailMutation.data.failed_count} imported emails failed processing.</p> : null}
          {gmailMutation.error && <p className="mt-2 text-sm text-red-700">{gmailMutation.error.message}</p>}
        </section>
      </div>
    </div>
  );
}
