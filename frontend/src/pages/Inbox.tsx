import { FormEvent, type ReactNode, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Apple, FileText, FolderSync, Inbox as InboxIcon, Loader2, Mail, Plus, StickyNote, Trash2, Upload } from 'lucide-react';
import { createManualItem, deleteItem, listItems, scanInboxFolder, uploadItem } from '../api/items';
import { getGmailStatus, syncGmail } from '../api/gmail';
import { getSettings } from '../api/views';

export default function Inbox() {
  const [note, setNote] = useState('');
  const queryClient = useQueryClient();
  const items = useQuery({ queryKey: ['items'], queryFn: listItems });
  const settings = useQuery({ queryKey: ['settings'], queryFn: getSettings });
  const gmailStatus = useQuery({ queryKey: ['gmail-status'], queryFn: getGmailStatus });
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
    mutationFn: (autoProcess?: boolean) => syncGmail(10, autoProcess),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['gmail-status'] });
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
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
        <ConnectorDashboard
          settings={settings.data}
          gmailStatus={gmailStatus.data}
          createPending={createMutation.isPending}
          uploadPending={uploadMutation.isPending}
          uploadError={uploadMutation.error}
          scanPending={scanMutation.isPending}
          scanResult={scanMutation.data}
          scanError={scanMutation.error}
          gmailPending={gmailMutation.isPending}
          gmailResult={gmailMutation.data}
          gmailError={gmailMutation.error}
        />
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
            Upload .txt, .md, or .pdf
            <input
              type="file"
              className="hidden"
              accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
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
            onClick={() => gmailMutation.mutate(undefined)}
            disabled={gmailMutation.isPending}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50"
          >
            {gmailMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <InboxIcon size={16} />}
            Sync Gmail
          </button>
          <button
            type="button"
            onClick={() => gmailMutation.mutate(false)}
            disabled={gmailMutation.isPending}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 disabled:opacity-50"
          >
            {gmailMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <InboxIcon size={16} />}
            Sync without auto-process
          </button>
          <div className="mt-3 space-y-1 text-sm text-slate-600">
            <div>Query: {gmailStatus.data?.query ?? settings.data?.gmail_query ?? 'label:SecondBrain'}</div>
            <div>Status: {gmailStatus.data?.status ?? settings.data?.gmail_status ?? 'unknown'}</div>
            {gmailStatus.data?.last_sync && (
              <div>
                Last sync: {gmailStatus.data.last_sync.status} · imported {gmailStatus.data.last_sync.imported_count} · processed {gmailStatus.data.last_sync.processed_count} · skipped {gmailStatus.data.last_sync.skipped_count}
              </div>
            )}
          </div>
          {gmailMutation.data && (
            <p className="mt-2 text-sm text-slate-600">
              Imported {gmailMutation.data.imported_count}; processed {gmailMutation.data.processed_count}; skipped {gmailMutation.data.skipped_count}; mode {gmailMutation.data.auto_process ? 'auto-process' : 'sync only'}
            </p>
          )}
          {gmailMutation.data?.failed_count ? <p className="mt-2 text-sm text-red-700">{gmailMutation.data.failed_count} imported emails failed processing.</p> : null}
          {gmailMutation.error && <p className="mt-2 text-sm text-red-700">{gmailMutation.error.message}</p>}
        </section>
      </div>
    </div>
  );
}

type ConnectorDashboardProps = {
  settings?: {
    inbox_folder: string;
    gmail_query: string;
    gmail_status: string;
    gmail_last_sync: { status: string; imported_count: number; processed_count: number; skipped_count: number; failed_count: number; error?: string | null } | null;
  };
  gmailStatus?: {
    status: string;
    query: string;
    last_sync: { status: string; imported_count: number; processed_count: number; skipped_count: number; failed_count: number; error?: string | null } | null;
  };
  createPending: boolean;
  uploadPending: boolean;
  uploadError: Error | null;
  scanPending: boolean;
  scanResult?: { created_count: number; skipped_count: number; folder: string };
  scanError: Error | null;
  gmailPending: boolean;
  gmailResult?: { status: string; imported_count: number; processed_count: number; skipped_count: number; failed_count: number; auto_process: boolean };
  gmailError: Error | null;
};

function ConnectorDashboard(props: ConnectorDashboardProps) {
  const lastGmail = props.gmailStatus?.last_sync ?? props.settings?.gmail_last_sync ?? null;
  const gmailStatus = props.gmailStatus?.status ?? props.settings?.gmail_status ?? 'unknown';
  const gmailQuery = props.gmailStatus?.query ?? props.settings?.gmail_query ?? 'label:SecondBrain';
  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold">Ways to Bring in Data</h2>
        <Link to="/settings" className="text-xs font-medium text-slate-600 hover:text-slate-900">Settings</Link>
      </div>
      <div className="grid gap-3">
        <ConnectorTile
          icon={<StickyNote size={16} />}
          title="Manual note"
          status={props.createPending ? 'working' : 'ready'}
          setup="Ready"
          detail="Type or paste notes directly into the inbox."
          nextAction="Add a note below."
        />
        <ConnectorTile
          icon={<Upload size={16} />}
          title="File upload"
          status={props.uploadPending ? 'uploading' : props.uploadError ? 'error' : 'ready'}
          setup=".txt, .md, .pdf"
          detail={props.uploadError ? props.uploadError.message : 'Upload supported text and PDF files.'}
          nextAction="Use the upload control below."
        />
        <ConnectorTile
          icon={<FolderSync size={16} />}
          title="Folder inbox"
          status={props.scanPending ? 'scanning' : props.scanError ? 'error' : 'ready'}
          setup={props.settings?.inbox_folder ?? 'Configured in Settings'}
          detail={
            props.scanError
              ? props.scanError.message
              : props.scanResult
                ? `Last scan imported ${props.scanResult.created_count}; skipped ${props.scanResult.skipped_count}.`
                : 'Drop files into the configured folder and scan manually.'
          }
          nextAction="Run Scan inbox folder."
        />
        <ConnectorTile
          icon={<Mail size={16} />}
          title="Gmail label sync"
          status={props.gmailPending ? 'syncing' : props.gmailError || lastGmail?.status === 'failed' ? 'error' : gmailStatus}
          setup={gmailQuery}
          detail={
            props.gmailError
              ? props.gmailError.message
              : props.gmailResult
                ? `Latest sync imported ${props.gmailResult.imported_count}; processed ${props.gmailResult.processed_count}; skipped ${props.gmailResult.skipped_count}.`
                : lastGmail
                  ? `Last sync ${lastGmail.status}: imported ${lastGmail.imported_count}; processed ${lastGmail.processed_count}; skipped ${lastGmail.skipped_count}.`
                  : 'Sync messages that match your Gmail query.'
          }
          nextAction={gmailStatus === 'ready' ? 'Run Sync Gmail.' : 'Check Gmail setup in Settings.'}
        />
        <ConnectorTile
          icon={<Apple size={16} />}
          title="Apple Notes export"
          status="manual"
          setup="Folder or Gmail"
          detail="Export notes as files or email them with your SecondBrain label."
          nextAction="Use folder scan or Gmail sync."
        />
        <ConnectorTile
          icon={<FileText size={16} />}
          title="More connectors"
          status="planned"
          setup="Roadmap"
          detail="Notion, Google Drive, Sheets, bookmarks, Slack, GitHub, and more are tracked in TODO."
          nextAction="Pick the next connector from the backlog."
        />
      </div>
    </section>
  );
}

function ConnectorTile({
  icon,
  title,
  status,
  setup,
  detail,
  nextAction
}: {
  icon: ReactNode;
  title: string;
  status: string;
  setup: string;
  detail: string;
  nextAction: string;
}) {
  const tone = connectorTone(status);
  return (
    <div className="rounded-md border border-slate-200 px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2 text-sm font-medium text-slate-800">
          <span className="text-slate-500">{icon}</span>
          <span>{title}</span>
        </div>
        <span className={`shrink-0 rounded px-2 py-0.5 text-xs ${tone}`}>{status}</span>
      </div>
      <div className="mt-2 truncate text-xs text-slate-500">{setup}</div>
      <p className="mt-2 text-sm leading-5 text-slate-600">{detail}</p>
      <div className="mt-2 text-xs font-medium text-slate-500">{nextAction}</div>
    </div>
  );
}

function connectorTone(status: string) {
  const normalized = status.toLowerCase();
  if (normalized.includes('error') || normalized.includes('failed') || normalized.includes('missing')) return 'bg-rose-50 text-rose-700';
  if (normalized.includes('working') || normalized.includes('uploading') || normalized.includes('scanning') || normalized.includes('syncing')) return 'bg-amber-50 text-amber-700';
  if (normalized.includes('ready') || normalized.includes('succeeded')) return 'bg-emerald-50 text-emerald-700';
  return 'bg-slate-100 text-slate-700';
}
