import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { BookOpen, FileText, FileVideo, Loader2, Paperclip, Play, Trash2 } from 'lucide-react';
import { FileAsset, ItemDetailResponse, MediaArtifact, Memory, cancelProcessingRun, deleteItem, generateBookBrief, getItem, processItem, retryProcessingRun } from '../api/items';
import { deleteMemory, patchMemory } from '../api/memories';
import { createDecision, createIdea, createQuestion, createTask, patchDecision, patchIdea, patchQuestion, patchTask } from '../api/review';
import ExtractionReview, { ExtractionReviewPayload } from '../components/ExtractionReview';

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const item = useQuery({
    queryKey: ['item', id],
    queryFn: () => getItem(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data;
      const status = data?.latest_processing_run?.status;
      const hasActiveChunks = data?.document_chunks.some((chunk) => ['pending', 'processing'].includes(chunk.latest_processing_run?.status ?? chunk.item.status));
      return status === 'pending' || status === 'processing' || data?.item.status === 'extracting' || hasActiveChunks ? 2000 : false;
    }
  });
  const processMutation = useMutation({
    mutationFn: () => processItem(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const bookBriefMutation = useMutation({
    mutationFn: () => generateBookBrief(id!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const saveReviewMutation = useMutation({
    mutationFn: async ({ memoryId, payload }: { memoryId: string; payload: ExtractionReviewPayload }) => {
      await patchMemory(memoryId, { summary: payload.summary, tags: payload.tags });
      await Promise.all([
        ...payload.tasks
          .filter((task) => task.title.trim())
          .map((task) =>
            task.isNew
              ? createTask({
                  memory_id: memoryId,
                  title: task.title.trim(),
                  description: task.description.trim() || null,
                  priority: task.priority || null,
                  status: task.status
                })
              : patchTask(task.id, {
                  title: task.title,
                  description: task.description.trim() || null,
                  priority: task.priority || null,
                  status: task.status
                })
          ),
        ...payload.ideas
          .filter((idea) => idea.body.trim())
          .map((idea) =>
            idea.isNew
              ? createIdea({ memory_id: memoryId, body: idea.body.trim(), status: idea.status })
              : patchIdea(idea.id, { body: idea.body, status: idea.status })
          ),
        ...payload.decisions
          .filter((decision) => decision.title.trim())
          .map((decision) =>
            decision.isNew
              ? createDecision({
                  memory_id: memoryId,
                  title: decision.title.trim(),
                  rationale: decision.rationale.trim() || null,
                  confidence: decision.confidence
                })
              : patchDecision(decision.id, {
                  title: decision.title,
                  rationale: decision.rationale.trim() || null,
                  confidence: decision.confidence
                })
          ),
        ...payload.open_questions
          .filter((question) => question.question.trim())
          .map((question) =>
            question.isNew
              ? createQuestion({ memory_id: memoryId, question: question.question.trim(), status: question.status })
              : patchQuestion(question.id, { question: question.question, status: question.status })
          )
      ]);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const deleteItemMutation = useMutation({
    mutationFn: () => deleteItem(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['items'] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
      navigate('/');
    }
  });
  const deleteMemoryMutation = useMutation({
    mutationFn: deleteMemory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['item', id] });
      queryClient.invalidateQueries({ queryKey: ['memories'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({ queryKey: ['graph'] });
    }
  });
  const cancelRunMutation = useMutation({
    mutationFn: cancelProcessingRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });
  const retryRunMutation = useMutation({
    mutationFn: retryProcessingRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['item', id] })
  });

  if (item.isLoading) return <div>Loading...</div>;
  if (!item.data) return <div>Item not found.</div>;
  const latestRun = item.data.latest_processing_run;
  const activeProcessing = latestRun?.status === 'pending' || latestRun?.status === 'processing';
  const isChunkedPdfParent = item.data.item.content_type === 'application/pdf' && (item.data.item.status === 'extracting' || item.data.item.status === 'chunked' || item.data.document_chunks.length > 0);
  const chunkStats = getChunkStats(item.data.document_chunks);
  const hasBookBrief = item.data.memories.some((memory) => memory.memory_type === 'resource' && memory.tags.includes('Book Brief'));
  const canGenerateBookBrief = isChunkedPdfParent && chunkStats.total > 0 && chunkStats.active === 0 && chunkStats.failed === 0 && chunkStats.withMemories === chunkStats.total && !hasBookBrief;

  return (
    <div className="space-y-5">
      <section className="rounded-md border border-slate-200 bg-white p-4">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">{item.data.item.title}</h1>
            <div className="mt-1 text-sm text-slate-500">{item.data.item.status}</div>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button
              onClick={() => processMutation.mutate()}
              disabled={isChunkedPdfParent || processMutation.isPending || Boolean(activeProcessing) || deleteItemMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
              title={isChunkedPdfParent ? 'PDF knowledge extraction runs through chunks automatically.' : 'Process item'}
            >
              {processMutation.isPending || activeProcessing ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
              {isChunkedPdfParent ? 'Chunks auto-process' : processMutation.isPending ? 'Queueing' : activeProcessing ? latestRun?.status : 'Process'}
            </button>
            {isChunkedPdfParent && (
              <button
                type="button"
                onClick={() => bookBriefMutation.mutate()}
                disabled={!canGenerateBookBrief || bookBriefMutation.isPending || activeProcessing}
                className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                title={
                  hasBookBrief
                    ? 'Book Brief already exists.'
                    : canGenerateBookBrief
                      ? 'Generate a parent-level brief from all processed PDF chunks.'
                      : 'Book Brief requires all chunks to finish successfully first.'
                }
              >
                {bookBriefMutation.isPending || (activeProcessing && latestRun?.prompt_version === 'book_brief_v1') ? <Loader2 size={16} className="animate-spin" /> : <BookOpen size={16} />}
                {hasBookBrief ? 'Book Brief Ready' : 'Generate Book Brief'}
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete inbox item "${item.data.item.title}" and all extracted records?`)) {
                  deleteItemMutation.mutate();
                }
              }}
              disabled={deleteItemMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-rose-200 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              title="Delete inbox item"
            >
              {deleteItemMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Delete
            </button>
          </div>
        </div>
        {(processMutation.isPending || activeProcessing) && (
          <div className="mb-4 flex items-center gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            <Loader2 size={16} className="animate-spin" />
            {activeProcessing
              ? `Processing run ${latestRun?.status}. This page will refresh until extraction finishes.`
              : 'Queueing structured extraction.'}
          </div>
        )}
        {isChunkedPdfParent && (
          <div className="mb-4 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
            PDF extraction runs through page-aware chunks. Generate a Book Brief after every chunk finishes to create one parent-level synthesis.
          </div>
        )}
        <pre className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-800">{item.data.item.body_text}</pre>
        {item.data.file_assets.length > 0 && <MediaPanel fileAssets={item.data.file_assets} />}
        {processMutation.error && <p className="mt-3 text-sm text-red-700">{processMutation.error.message}</p>}
      </section>
      {item.data.document_chunks.length > 0 && (
        <DocumentChunksPanel
          chunks={item.data.document_chunks}
          onRetryChunk={(runId) => retryRunMutation.mutate(runId)}
          isRetrying={retryRunMutation.isPending}
        />
      )}
      {item.data.latest_processing_run && (
        <section className="rounded-md border border-slate-200 bg-white p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Extraction Diagnostics</h2>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
              <span className="rounded-md bg-slate-100 px-2 py-1">{latestRun?.status}</span>
              <span className="rounded-md bg-slate-100 px-2 py-1">{latestRun?.model}</span>
              {latestRun?.status === 'pending' && (
                <button
                  type="button"
                  onClick={() => cancelRunMutation.mutate(latestRun.id)}
                  disabled={cancelRunMutation.isPending}
                  className="rounded-md border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Cancel
                </button>
              )}
              {(latestRun?.status === 'failed' || latestRun?.status === 'canceled') && (
                <button
                  type="button"
                  onClick={() => retryRunMutation.mutate(latestRun.id)}
                  disabled={retryRunMutation.isPending}
                  className="rounded-md border border-slate-300 px-2 py-1 text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
          {item.data.latest_processing_run.error && <p className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{item.data.latest_processing_run.error}</p>}
          <div className="grid gap-3 lg:grid-cols-2">
            <DiagnosticBlock title="Original Output" value={item.data.latest_processing_run.original_output || item.data.latest_processing_run.raw_output} />
            <DiagnosticBlock title="Repaired Output" value={item.data.latest_processing_run.repaired_output} empty="No repair attempt was stored for this run." />
            <DiagnosticBlock title="Parsed JSON" value={formatJson(item.data.latest_processing_run.parsed_json)} className="lg:col-span-2" />
          </div>
        </section>
      )}
      {item.data.memories.map((memory) => (
        <section key={memory.id} className="rounded-md border border-slate-200 bg-white p-4">
          <div className="mb-3 flex justify-end">
            <button
              type="button"
              onClick={() => {
                if (window.confirm('Delete this memory and its extracted records? The source inbox item will stay.')) {
                  deleteMemoryMutation.mutate(memory.id);
                }
              }}
              disabled={deleteMemoryMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-rose-200 px-3 py-2 text-sm text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              title="Delete memory"
            >
              {deleteMemoryMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              Delete Memory
            </button>
          </div>
          <ExtractionReview
            memory={memory}
            isSaving={saveReviewMutation.isPending}
            onSave={(payload) => saveReviewMutation.mutate({ memoryId: memory.id, payload })}
          />
        </section>
      ))}
      {saveReviewMutation.error && <p className="text-sm text-red-700">{saveReviewMutation.error.message}</p>}
      {deleteMemoryMutation.error && <p className="text-sm text-red-700">{deleteMemoryMutation.error.message}</p>}
      {bookBriefMutation.error && <p className="text-sm text-red-700">{bookBriefMutation.error.message}</p>}
      {cancelRunMutation.error && <p className="text-sm text-red-700">{cancelRunMutation.error.message}</p>}
      {retryRunMutation.error && <p className="text-sm text-red-700">{retryRunMutation.error.message}</p>}
      {deleteItemMutation.error && <p className="text-sm text-red-700">{deleteItemMutation.error.message}</p>}
    </div>
  );
}

function getChunkStats(chunks: ItemDetailResponse['document_chunks']) {
  return {
    total: chunks.length,
    processed: chunks.filter((chunk) => chunk.latest_processing_run?.status === 'succeeded' || chunk.item.status === 'processed').length,
    active: chunks.filter((chunk) => ['pending', 'processing'].includes(chunk.latest_processing_run?.status ?? chunk.item.status)).length,
    failed: chunks.filter((chunk) => chunk.latest_processing_run?.status === 'failed' || chunk.item.status === 'failed').length,
    withMemories: chunks.filter((chunk) => chunk.memories.length > 0).length
  };
}

function MediaPanel({ fileAssets }: { fileAssets: FileAsset[] }) {
  return (
    <div className="mt-4 rounded-md border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700">
        <Paperclip size={16} />
        Attached Files
      </div>
      <div className="divide-y divide-slate-200">
        {fileAssets.map((asset) => (
          <div key={asset.id} className="p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <FileVideo size={16} />
                  <span className="break-all">{asset.filename}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {asset.mime_type || 'unknown type'} {asset.size_bytes !== null ? `- ${formatBytes(asset.size_bytes)}` : ''}
                </div>
              </div>
              <StatusPill status={asset.media_artifacts.length ? overallMediaStatus(asset.media_artifacts) : asset.mime_type === 'application/pdf' ? 'stored' : 'pending'} />
            </div>
            <div className="mt-3 grid gap-2">
              {asset.media_artifacts.length === 0 && asset.mime_type === 'application/pdf' ? (
                <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">Original PDF stored. Text extraction and knowledge extraction are tracked in document chunks.</p>
              ) : asset.media_artifacts.length === 0 ? (
                <p className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">Media analysis has not run yet.</p>
              ) : (
                asset.media_artifacts.map((artifact) => <ArtifactBlock key={artifact.id} artifact={artifact} />)
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DocumentChunksPanel({
  chunks,
  onRetryChunk,
  isRetrying
}: {
  chunks: ItemDetailResponse['document_chunks'];
  onRetryChunk: (runId: string) => void;
  isRetrying: boolean;
}) {
  const processedCount = chunks.filter((chunk) => chunk.latest_processing_run?.status === 'succeeded' || chunk.item.status === 'processed').length;
  const activeCount = chunks.filter((chunk) => ['pending', 'processing'].includes(chunk.latest_processing_run?.status ?? chunk.item.status)).length;
  const failedCount = chunks.filter((chunk) => chunk.latest_processing_run?.status === 'failed' || chunk.item.status === 'failed').length;
  const memories = chunks.flatMap((chunk) => chunk.memories.map((memory) => ({ chunk, memory })));

  return (
    <details className="rounded-md border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer list-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">PDF Chunks</h2>
            <p className="mt-1 text-sm text-slate-500">
              {chunks.length} chunks; {processedCount} processed; {activeCount} active; {failedCount} failed.
            </p>
          </div>
          <span className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600">Expand chunks</span>
        </div>
      </summary>
      <div className="mt-4 grid gap-3">
        {chunks.map((chunk) => {
          const metadata = chunk.item.metadata_json ?? {};
          const pageStart = typeof metadata.page_start === 'number' ? metadata.page_start : null;
          const pageEnd = typeof metadata.page_end === 'number' ? metadata.page_end : null;
          const pageLabel = pageStart && pageEnd ? (pageStart === pageEnd ? `page ${pageStart}` : `pages ${pageStart}-${pageEnd}`) : 'pages unknown';
          return (
            <details key={chunk.item.id} className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <summary className="cursor-pointer text-sm font-medium text-slate-800">
                <span className="inline-flex items-center gap-2">
                  <FileText size={15} />
                  {pageLabel}
                  <StatusPill status={chunk.latest_processing_run?.status ?? chunk.item.status} />
                  {chunk.memories.length > 0 && <span className="text-xs text-slate-500">{chunk.memories.length} memories</span>}
                </span>
              </summary>
              {chunk.latest_processing_run?.error && <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800">{chunk.latest_processing_run.error}</p>}
              {chunk.latest_processing_run && ['failed', 'canceled'].includes(chunk.latest_processing_run.status) && (
                <button
                  type="button"
                  onClick={() => onRetryChunk(chunk.latest_processing_run!.id)}
                  disabled={isRetrying}
                  className="mt-3 inline-flex items-center gap-2 rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-white disabled:opacity-50"
                >
                  {isRetrying ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                  Retry chunk
                </button>
              )}
              {chunk.memories.length === 0 ? (
                <p className="mt-3 text-sm text-slate-600">No extracted memory for this chunk yet.</p>
              ) : (
                <div className="mt-3 space-y-3">
                  {chunk.memories.map((memory) => <ChunkMemory key={memory.id} memory={memory} />)}
                </div>
              )}
            </details>
          );
        })}
      </div>
      {memories.length > 0 && (
        <div className="mt-4 rounded-md border border-slate-200 bg-white p-3">
          <h3 className="text-sm font-semibold text-slate-700">Extracted Knowledge Preview</h3>
          <div className="mt-2 space-y-2">
            {memories.slice(0, 8).map(({ chunk, memory }) => (
              <div key={memory.id} className="rounded-md bg-slate-50 p-2 text-sm">
                <div className="text-xs text-slate-500">{chunk.item.title}</div>
                <div className="mt-1 text-slate-800">{memory.summary}</div>
                {memory.tags.length > 0 && <div className="mt-1 text-xs text-slate-500">Tags: {memory.tags.join(', ')}</div>}
              </div>
            ))}
            {memories.length > 8 && <p className="text-xs text-slate-500">+{memories.length - 8} more chunk memories</p>}
          </div>
        </div>
      )}
    </details>
  );
}

function ChunkMemory({ memory }: { memory: Memory }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3">
      <div className="text-sm text-slate-800">{memory.summary}</div>
      {memory.tags.length > 0 && <div className="mt-2 text-xs text-slate-500">Tags: {memory.tags.join(', ')}</div>}
      <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
        {memory.tasks.length > 0 && <span>{memory.tasks.length} tasks</span>}
        {memory.ideas.length > 0 && <span>{memory.ideas.length} ideas</span>}
        {memory.decisions.length > 0 && <span>{memory.decisions.length} decisions</span>}
        {memory.open_questions.length > 0 && <span>{memory.open_questions.length} questions</span>}
      </div>
    </div>
  );
}

function ArtifactBlock({ artifact }: { artifact: MediaArtifact }) {
  return (
    <details className="rounded-md border border-slate-200 bg-slate-50 p-3">
      <summary className="cursor-pointer text-sm font-medium text-slate-700">
        {artifact.artifact_type.replace(/_/g, ' ')} <StatusPill status={artifact.status} />
      </summary>
      {artifact.text_content && <pre className="mt-3 whitespace-pre-wrap text-xs text-slate-800">{artifact.text_content}</pre>}
      {artifact.stored_path && <p className="mt-2 break-all text-xs text-slate-500">{artifact.stored_path}</p>}
      {artifact.error && <p className="mt-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-800">{artifact.error}</p>}
    </details>
  );
}

function StatusPill({ status }: { status: string }) {
  const color = ['processed', 'succeeded', 'chunked', 'stored'].includes(status) ? 'bg-emerald-50 text-emerald-700' : status === 'failed' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700';
  return <span className={`inline-flex rounded-md px-2 py-1 text-xs font-medium ${color}`}>{status}</span>;
}

function overallMediaStatus(artifacts: MediaArtifact[]): string {
  if (!artifacts.length) return 'pending';
  if (artifacts.some((artifact) => artifact.status === 'failed')) return 'failed';
  if (artifacts.every((artifact) => artifact.status === 'processed')) return 'processed';
  return 'pending';
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function DiagnosticBlock({ title, value, empty, className = '' }: { title: string; value: string | null | undefined; empty?: string; className?: string }) {
  return (
    <details className={`rounded-md border border-slate-200 bg-slate-50 p-3 ${className}`}>
      <summary className="cursor-pointer text-sm font-semibold text-slate-700">{title}</summary>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-800">{value || empty || 'Nothing stored.'}</pre>
    </details>
  );
}

function formatJson(value: unknown): string {
  if (!value) return '';
  return JSON.stringify(value, null, 2);
}
