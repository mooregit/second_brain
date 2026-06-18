import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, Check, Loader2, MessageSquareText, Pencil, Save, Trash2, X } from 'lucide-react';
import type { AskResponse } from '../api/ask';
import { OpenQuestion, listOpenQuestions, listProjects } from '../api/views';
import { answerQuestion, askQuestionRecord, deleteQuestion, patchQuestion } from '../api/review';
import SourceLink from '../components/SourceLink';

export default function OpenQuestions() {
  const queryClient = useQueryClient();
  const [showArchived, setShowArchived] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState({ question: '', status: 'open', project_id: '' });
  const [answeringId, setAnsweringId] = useState<string | null>(null);
  const [answerDraft, setAnswerDraft] = useState('');
  const [answerConfidence, setAnswerConfidence] = useState(0.7);
  const [proposedAnswers, setProposedAnswers] = useState<Record<string, AskResponse>>({});
  const questions = useQuery({ queryKey: ['open-questions', showArchived], queryFn: () => listOpenQuestions(showArchived) });
  const projects = useQuery({ queryKey: ['projects'], queryFn: listProjects });
  const patchMutation = useMutation({
    mutationFn: ({ questionId, payload }: { questionId: string; payload: typeof draft }) =>
      patchQuestion(questionId, { question: payload.question.trim(), status: payload.status, project_id: payload.project_id || null }),
    onSuccess: () => {
      setEditingId(null);
      invalidate();
    }
  });
  const deleteMutation = useMutation({ mutationFn: deleteQuestion, onSuccess: invalidate });
  const askMutation = useMutation({
    mutationFn: (questionId: string) => askQuestionRecord(questionId),
    onSuccess: (answer, questionId) => {
      setProposedAnswers((current) => ({ ...current, [questionId]: answer }));
      setAnsweringId(questionId);
      setAnswerDraft(answer.answer);
      setAnswerConfidence(answer.sources.length ? Math.min(0.95, Math.max(0.55, answer.sources[0].score)) : 0.3);
    }
  });
  const answerMutation = useMutation({
    mutationFn: ({ questionId, answer, confidence, sources }: { questionId: string; answer: string; confidence: number; sources: AskResponse['sources'] }) =>
      answerQuestion(questionId, { answer_text: answer, answer_confidence: confidence, answer_sources_json: sources }),
    onSuccess: () => {
      setAnsweringId(null);
      setAnswerDraft('');
      invalidate();
    }
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['open-questions'] });
    queryClient.invalidateQueries({ queryKey: ['memories'] });
    queryClient.invalidateQueries({ queryKey: ['graph'] });
    queryClient.invalidateQueries({ queryKey: ['projects'] });
  }

  function startEdit(question: OpenQuestion) {
    setEditingId(question.id);
    setDraft({ question: question.question, status: question.status, project_id: question.project_id ?? '' });
  }

  function startManualAnswer(question: OpenQuestion) {
    setAnsweringId(question.id);
    setAnswerDraft(question.answer_text ?? '');
    setAnswerConfidence(question.answer_confidence ?? 0.7);
  }

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
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                {editingId === question.id ? (
                  <div className="space-y-2">
                    <textarea className="h-20 w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.question} onChange={(event) => setDraft({ ...draft, question: event.target.value })} />
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}>
                      <option value="open">Open</option>
                      <option value="answered">Answered</option>
                      <option value="archived">Archived</option>
                    </select>
                    <select className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm" value={draft.project_id} onChange={(event) => setDraft({ ...draft, project_id: event.target.value })}>
                      <option value="">No project</option>
                      {projects.data?.map((project) => (
                        <option key={project.id} value={project.id}>{project.name}</option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-medium">{question.question}</h2>
                      <span className="rounded bg-slate-100 px-2 py-1 text-xs">{question.status}</span>
                    </div>
                    <div className="mt-2 text-sm"><SourceLink rawItemId={question.source_raw_item_id} label="Source" /></div>
                    {question.answer_text && (
                      <div className="mt-3 rounded-md border border-emerald-100 bg-emerald-50 p-3 text-sm">
                        <div className="mb-1 flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-wide text-emerald-800">
                          Answered
                          {question.answer_confidence !== null && <span>confidence {question.answer_confidence.toFixed(2)}</span>}
                        </div>
                        <p className="whitespace-pre-wrap text-emerald-950">{question.answer_text}</p>
                        {question.answer_sources_json.length > 0 && (
                          <div className="mt-2 space-y-1">
                            {question.answer_sources_json.map((source, index) => (
                              <div key={index} className="text-xs text-emerald-800">
                                {source.raw_item_id ? <SourceLink rawItemId={source.raw_item_id} label={source.title || `Source ${index + 1}`} /> : source.title || `Source ${index + 1}`}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    {answeringId === question.id && (
                      <div className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                        <label className="block text-xs font-medium text-slate-600">
                          Answer
                          <textarea
                            className="mt-1 h-36 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                            value={answerDraft}
                            onChange={(event) => setAnswerDraft(event.target.value)}
                          />
                        </label>
                        <label className="mt-2 block text-xs font-medium text-slate-600">
                          Confidence
                          <input
                            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                            type="number"
                            min="0"
                            max="1"
                            step="0.05"
                            value={answerConfidence}
                            onChange={(event) => setAnswerConfidence(Number(event.target.value))}
                          />
                        </label>
                        {proposedAnswers[question.id]?.sources.length ? (
                          <div className="mt-2 space-y-1 text-xs text-slate-600">
                            {proposedAnswers[question.id].sources.map((source) => (
                              <div key={`${source.owner_type}:${source.owner_id}`}>
                                {source.raw_item_id ? <SourceLink rawItemId={source.raw_item_id} label={source.title} /> : source.title} · {source.score.toFixed(3)}
                              </div>
                            ))}
                          </div>
                        ) : null}
                        <div className="mt-3 flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              answerMutation.mutate({
                                questionId: question.id,
                                answer: answerDraft.trim(),
                                confidence: answerConfidence,
                                sources: proposedAnswers[question.id]?.sources ?? []
                              })
                            }
                            disabled={answerMutation.isPending || !answerDraft.trim()}
                            className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
                          >
                            {answerMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                            Save answer
                          </button>
                          <button type="button" onClick={() => setAnsweringId(null)} className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-white">
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {editingId === question.id ? (
                  <>
                    <button type="button" onClick={() => patchMutation.mutate({ questionId: question.id, payload: draft })} disabled={patchMutation.isPending || !draft.question.trim()} className="rounded-md border border-emerald-200 p-1.5 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50" title="Save open question">
                      <Check size={14} />
                    </button>
                    <button type="button" onClick={() => setEditingId(null)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Cancel edit">
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <button type="button" onClick={() => startEdit(question)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Edit open question">
                      <Pencil size={14} />
                    </button>
                    <button type="button" onClick={() => askMutation.mutate(question.id)} disabled={askMutation.isPending} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-50" title="Ask Second Brain">
                      {askMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <MessageSquareText size={14} />}
                    </button>
                    <button type="button" onClick={() => startManualAnswer(question)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Answer manually">
                      <Check size={14} />
                    </button>
                    {question.status !== 'archived' && (
                      <button type="button" onClick={() => patchQuestion(question.id, { status: 'archived' }).then(invalidate)} className="rounded-md border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-50" title="Archive open question">
                        <Archive size={14} />
                      </button>
                    )}
                    <button type="button" onClick={() => window.confirm('Delete this open question?') && deleteMutation.mutate(question.id)} disabled={deleteMutation.isPending} className="rounded-md border border-rose-200 p-1.5 text-rose-700 hover:bg-rose-50 disabled:opacity-50" title="Delete open question">
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
