import { FormEvent, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, FolderSync, GitBranch, Loader2, Mail, Save, StickyNote, Upload } from 'lucide-react';
import { syncGitHub, type GitHubSyncResult } from '../api/github';
import { syncGitLab, type GitLabSyncResult } from '../api/gitlab';
import { getSettings, listOllamaModels, patchSettings, type Settings as AppSettings } from '../api/views';

export default function Settings() {
  const [inboxFolder, setInboxFolder] = useState('');
  const [extractionModel, setExtractionModel] = useState('');
  const [embeddingModel, setEmbeddingModel] = useState('');
  const [gmailEnabled, setGmailEnabled] = useState(false);
  const [gmailLabel, setGmailLabel] = useState('');
  const [gmailQuery, setGmailQuery] = useState('');
  const [gmailAutoProcess, setGmailAutoProcess] = useState(true);
  const [gitlabEnabled, setGitlabEnabled] = useState(false);
  const [gitlabBaseUrl, setGitlabBaseUrl] = useState('https://gitlab.com');
  const [gitlabToken, setGitlabToken] = useState('');
  const [gitlabProjects, setGitlabProjects] = useState('');
  const [gitlabAutoProcess, setGitlabAutoProcess] = useState(true);
  const [gitlabMaxResults, setGitlabMaxResults] = useState(20);
  const [githubEnabled, setGithubEnabled] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [githubRepositories, setGithubRepositories] = useState('');
  const [githubAutoProcess, setGithubAutoProcess] = useState(true);
  const [githubMaxResults, setGithubMaxResults] = useState(20);
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
        gmail_auto_process: gmailAutoProcess,
        gitlab_enabled: gitlabEnabled,
        gitlab_base_url: gitlabBaseUrl,
        gitlab_projects: gitlabProjects,
        gitlab_auto_process: gitlabAutoProcess,
        github_enabled: githubEnabled,
        github_repositories: githubRepositories,
        github_auto_process: githubAutoProcess,
        ...(gitlabToken.trim() ? { gitlab_token: gitlabToken.trim() } : {}),
        ...(githubToken.trim() ? { github_token: githubToken.trim() } : {})
      }),
    onSuccess: (data) => {
      setInboxFolder(data.inbox_folder);
      setExtractionModel(data.ollama_extraction_model);
      setEmbeddingModel(data.ollama_embedding_model);
      setGmailEnabled(data.gmail_enabled);
      setGmailLabel(data.gmail_label);
      setGmailQuery(data.gmail_query);
      setGmailAutoProcess(data.gmail_auto_process);
      setGitlabEnabled(data.gitlab_enabled);
      setGitlabBaseUrl(data.gitlab_base_url);
      setGitlabProjects(data.gitlab_projects);
      setGitlabAutoProcess(data.gitlab_auto_process);
      setGitlabToken('');
      setGithubEnabled(data.github_enabled);
      setGithubRepositories(data.github_repositories);
      setGithubAutoProcess(data.github_auto_process);
      setGithubToken('');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });
  const githubSync = useMutation({
    mutationFn: () => syncGitHub({ max_results: githubMaxResults, auto_process: githubAutoProcess }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['processing-runs'] });
    }
  });
  const gitlabSync = useMutation({
    mutationFn: () => syncGitLab({ max_results: gitlabMaxResults, auto_process: gitlabAutoProcess }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['processing-runs'] });
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
      setGitlabEnabled(settings.data.gitlab_enabled);
      setGitlabBaseUrl(settings.data.gitlab_base_url);
      setGitlabProjects(settings.data.gitlab_projects);
      setGitlabAutoProcess(settings.data.gitlab_auto_process);
      setGithubEnabled(settings.data.github_enabled);
      setGithubRepositories(settings.data.github_repositories);
      setGithubAutoProcess(settings.data.github_auto_process);
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
          <IngestionGuide settings={settings.data} githubSyncResult={githubSync.data} gitlabSyncResult={gitlabSync.data} />
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
            <dt className="font-medium text-slate-600">GitLab</dt>
            <dd>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{settings.data.gitlab_status}</span>
              <span className={`ml-2 rounded px-2 py-1 text-xs ${settings.data.gitlab_token_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {settings.data.gitlab_token_configured ? 'token configured' : 'missing token'}
              </span>
            </dd>
            <dt className="font-medium text-slate-600">Latest GitLab sync</dt>
            <dd>
              {settings.data.gitlab_last_sync
                ? `${settings.data.gitlab_last_sync.status}: imported ${settings.data.gitlab_last_sync.imported_count}, queued ${settings.data.gitlab_last_sync.queued_count ?? 0}, skipped ${settings.data.gitlab_last_sync.skipped_count}`
                : 'none'}
            </dd>
            <dt className="font-medium text-slate-600">GitHub</dt>
            <dd>
              <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{settings.data.github_status}</span>
              <span className={`ml-2 rounded px-2 py-1 text-xs ${settings.data.github_token_configured ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {settings.data.github_token_configured ? 'token configured' : 'missing token'}
              </span>
            </dd>
            <dt className="font-medium text-slate-600">Latest GitHub sync</dt>
            <dd>
              {settings.data.github_last_sync
                ? `${settings.data.github_last_sync.status}: imported ${settings.data.github_last_sync.imported_count}, queued ${settings.data.github_last_sync.queued_count ?? 0}, skipped ${settings.data.github_last_sync.skipped_count}`
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
            <div className="grid gap-3 border-t border-slate-200 pt-4 md:grid-cols-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 md:col-span-2">
                <GitBranch size={16} />
                GitHub
              </div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={githubEnabled} onChange={(event) => setGithubEnabled(event.target.checked)} />
                GitHub enabled
              </label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={githubAutoProcess} onChange={(event) => setGithubAutoProcess(event.target.checked)} />
                Auto-process imported GitHub items
              </label>
              <label className="block text-sm font-medium text-slate-700 md:col-span-2">
                Personal access token
                <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" type="password" value={githubToken} onChange={(event) => setGithubToken(event.target.value)} placeholder={settings.data.github_token_configured ? 'Leave blank to keep existing token' : 'github_pat_...'} />
              </label>
              <label className="block text-sm font-medium text-slate-700 md:col-span-2">
                Repositories
                <textarea className="mt-1 h-24 w-full rounded-md border border-slate-300 px-3 py-2" value={githubRepositories} onChange={(event) => setGithubRepositories(event.target.value)} placeholder="owner/repo&#10;another-owner/another-repo" />
              </label>
              <div className="flex flex-wrap items-end gap-3 md:col-span-2">
                <label className="block text-sm font-medium text-slate-700">
                  Max issues/PRs per repo
                  <input className="mt-1 w-36 rounded-md border border-slate-300 px-3 py-2" type="number" min={1} max={100} value={githubMaxResults} onChange={(event) => setGithubMaxResults(Number(event.target.value))} />
                </label>
                <button
                  type="button"
                  onClick={() => githubSync.mutate()}
                  disabled={githubSync.isPending || settings.data.github_status !== 'ready'}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {githubSync.isPending ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
                  Sync GitHub
                </button>
                {githubSync.data && (
                  <span className="text-sm text-slate-600">
                    Imported {githubSync.data.imported_count}, queued {githubSync.data.queued_count}, skipped {githubSync.data.skipped_count}.
                  </span>
                )}
              </div>
              {githubSync.error && <p className="text-sm text-red-700 md:col-span-2">{githubSync.error.message}</p>}
            </div>
            <div className="grid gap-3 border-t border-slate-200 pt-4 md:grid-cols-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800 md:col-span-2">
                <GitBranch size={16} />
                GitLab
              </div>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={gitlabEnabled} onChange={(event) => setGitlabEnabled(event.target.checked)} />
                GitLab enabled
              </label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <input type="checkbox" checked={gitlabAutoProcess} onChange={(event) => setGitlabAutoProcess(event.target.checked)} />
                Auto-process imported GitLab items
              </label>
              <label className="block text-sm font-medium text-slate-700">
                GitLab base URL
                <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" value={gitlabBaseUrl} onChange={(event) => setGitlabBaseUrl(event.target.value)} placeholder="https://gitlab.com" />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Personal access token
                <input className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" type="password" value={gitlabToken} onChange={(event) => setGitlabToken(event.target.value)} placeholder={settings.data.gitlab_token_configured ? 'Leave blank to keep existing token' : 'glpat-...'} />
              </label>
              <label className="block text-sm font-medium text-slate-700 md:col-span-2">
                Project paths
                <textarea className="mt-1 h-24 w-full rounded-md border border-slate-300 px-3 py-2" value={gitlabProjects} onChange={(event) => setGitlabProjects(event.target.value)} placeholder="group/project&#10;another-group/another-project" />
              </label>
              <div className="flex flex-wrap items-end gap-3 md:col-span-2">
                <label className="block text-sm font-medium text-slate-700">
                  Max issues/MRs per project
                  <input className="mt-1 w-36 rounded-md border border-slate-300 px-3 py-2" type="number" min={1} max={100} value={gitlabMaxResults} onChange={(event) => setGitlabMaxResults(Number(event.target.value))} />
                </label>
                <button
                  type="button"
                  onClick={() => gitlabSync.mutate()}
                  disabled={gitlabSync.isPending || settings.data.gitlab_status !== 'ready'}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  {gitlabSync.isPending ? <Loader2 size={16} className="animate-spin" /> : <GitBranch size={16} />}
                  Sync GitLab
                </button>
                {gitlabSync.data && (
                  <span className="text-sm text-slate-600">
                    Imported {gitlabSync.data.imported_count}, queued {gitlabSync.data.queued_count}, skipped {gitlabSync.data.skipped_count}.
                  </span>
                )}
              </div>
              {gitlabSync.error && <p className="text-sm text-red-700 md:col-span-2">{gitlabSync.error.message}</p>}
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

function IngestionGuide({
  settings,
  githubSyncResult,
  gitlabSyncResult
}: {
  settings: AppSettings;
  githubSyncResult?: GitHubSyncResult;
  gitlabSyncResult?: GitLabSyncResult;
}) {
  return (
    <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold">Ways to Bring in Data</h2>
        <span className="text-xs text-slate-500">Configure connectors here, then sync from their sections below.</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ConnectorTile
          icon={<StickyNote size={16} />}
          title="Manual note"
          status="ready"
          setup="Inbox"
          detail="Type or paste notes directly from the Inbox page."
          nextAction="Use Manual Note on the Inbox page."
        />
        <ConnectorTile
          icon={<Upload size={16} />}
          title="File upload"
          status="ready"
          setup=".txt, .md, .pdf"
          detail="Upload text, Markdown, and PDF files from the Inbox page."
          nextAction="Use File Inputs on the Inbox page."
        />
        <ConnectorTile
          icon={<FolderSync size={16} />}
          title="Folder inbox"
          status="ready"
          setup={settings.inbox_folder}
          detail="Drop supported files into the configured inbox folder and scan them."
          nextAction="Run Scan inbox folder from the Inbox page."
        />
        <ConnectorTile
          icon={<Mail size={16} />}
          title="Gmail label sync"
          status={settings.gmail_status}
          setup={settings.gmail_query}
          detail={
            settings.gmail_last_sync
              ? `Last sync ${settings.gmail_last_sync.status}: imported ${settings.gmail_last_sync.imported_count}; queued ${settings.gmail_last_sync.queued_count ?? 0}; skipped ${settings.gmail_last_sync.skipped_count}.`
              : 'Sync messages matching your configured Gmail query.'
          }
          nextAction={settings.gmail_status === 'ready' ? 'Run Sync Gmail from the Inbox page.' : 'Finish Gmail setup below.'}
        />
        <ConnectorTile
          icon={<GitBranch size={16} />}
          title="GitHub sync"
          status={settings.github_status}
          setup={settings.github_repositories || 'owner/repo'}
          detail={
            githubSyncResult
              ? `Latest sync imported ${githubSyncResult.imported_count}; queued ${githubSyncResult.queued_count}; skipped ${githubSyncResult.skipped_count}.`
              : settings.github_last_sync
                ? `Last sync ${settings.github_last_sync.status}: imported ${settings.github_last_sync.imported_count}; queued ${settings.github_last_sync.queued_count}; skipped ${settings.github_last_sync.skipped_count}.`
                : 'Sync open issues, pull requests, and failing GitHub Actions runs.'
          }
          nextAction={settings.github_status === 'ready' ? 'Run Sync GitHub below.' : 'Add token and repositories below.'}
        />
        <ConnectorTile
          icon={<GitBranch size={16} />}
          title="GitLab sync"
          status={settings.gitlab_status}
          setup={settings.gitlab_projects || 'group/project'}
          detail={
            gitlabSyncResult
              ? `Latest sync imported ${gitlabSyncResult.imported_count}; queued ${gitlabSyncResult.queued_count}; skipped ${gitlabSyncResult.skipped_count}.`
              : settings.gitlab_last_sync
                ? `Last sync ${settings.gitlab_last_sync.status}: imported ${settings.gitlab_last_sync.imported_count}; queued ${settings.gitlab_last_sync.queued_count}; skipped ${settings.gitlab_last_sync.skipped_count}.`
                : 'Sync open issues and merge requests.'
          }
          nextAction={settings.gitlab_status === 'ready' ? 'Run Sync GitLab below.' : 'Optional: finish GitLab setup below.'}
        />
        <ConnectorTile
          icon={<FileText size={16} />}
          title="More connectors"
          status="planned"
          setup="Roadmap"
          detail="Good future candidates: docs, bookmarks, Slack, Drive, and repo contents."
          nextAction="Add the next connector when it becomes useful."
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
    <div className="rounded-md border border-slate-200 bg-white px-3 py-3">
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
