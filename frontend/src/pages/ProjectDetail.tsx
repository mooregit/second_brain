import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CheckSquare, CircleHelp, FileText, Lightbulb, Sparkles } from 'lucide-react';
import SourceLink from '../components/SourceLink';
import { getProjectBrief } from '../api/views';

export default function ProjectDetail() {
  const { id } = useParams();
  const brief = useQuery({
    queryKey: ['project-brief', id],
    queryFn: () => getProjectBrief(id ?? ''),
    enabled: Boolean(id)
  });

  if (!id) return <p className="text-sm text-red-700">Project id is required.</p>;
  if (brief.isLoading) return <p className="text-sm text-slate-600">Loading project brief...</p>;
  if (brief.error) return <p className="text-sm text-red-700">{brief.error.message}</p>;
  if (!brief.data) return null;

  const data = brief.data;

  return (
    <section className="space-y-4">
      <Link to="/projects" className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900">
        <ArrowLeft size={16} />
        Projects
      </Link>
      <div className="rounded-md border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-sky-900">
              <Sparkles size={16} />
              Graphify Project Brief
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">{data.project.name}</h1>
            {data.project.description && <p className="mt-1 text-sm text-slate-600">{data.project.description}</p>}
          </div>
          <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-4">
            <CountPill label="Tasks" value={data.counts.open_tasks} />
            <CountPill label="Questions" value={data.counts.open_questions} />
            <CountPill label="Ideas" value={data.counts.active_ideas} />
            <CountPill label="Decisions" value={data.counts.decisions} />
          </div>
        </div>
        <p className="mt-4 rounded-md bg-sky-50 p-3 text-sm text-sky-950">{data.summary}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <BriefSection title="Next Actions" icon={<CheckSquare size={16} />}>
            {data.next_actions.map((action) => (
              <li key={action} className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700">
                {action}
              </li>
            ))}
          </BriefSection>

          <BriefSection title="Open Tasks" icon={<CheckSquare size={16} />}>
            {data.open_tasks.map((task) => (
              <li key={task.id} className="rounded-md border border-slate-200 bg-white p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-900">{task.title}</span>
                  <span className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">{task.status}</span>
                  {task.priority && <span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">{task.priority}</span>}
                </div>
                {task.description && <p className="mt-1 text-sm text-slate-600">{task.description}</p>}
                <div className="mt-2 text-sm"><SourceLink rawItemId={task.source_raw_item_id} label="Source" /></div>
              </li>
            ))}
            {data.open_tasks.length === 0 && <EmptyLine>No open tasks.</EmptyLine>}
          </BriefSection>

          <BriefSection title="Open Questions" icon={<CircleHelp size={16} />}>
            {data.open_questions.map((question) => (
              <li key={question.id} className="rounded-md border border-slate-200 bg-white p-3">
                <div className="font-medium text-slate-900">{question.question}</div>
                <div className="mt-2 text-sm"><SourceLink rawItemId={question.source_raw_item_id} label="Source" /></div>
              </li>
            ))}
            {data.open_questions.length === 0 && <EmptyLine>No open questions.</EmptyLine>}
          </BriefSection>
        </div>

        <aside className="space-y-4">
          <BriefSection title="Project Flags" icon={<Sparkles size={16} />}>
            {data.github_failures.map((failure) => (
              <li key={failure.raw_item_id} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-950">
                <div className="font-medium">GitHub Actions failing: {failure.name}</div>
                <div className="mt-1 text-xs text-red-800">
                  {failure.repository}
                  {failure.branch ? ` on ${failure.branch}` : ''} | {failure.conclusion}
                </div>
                <div className="mt-2"><SourceLink rawItemId={failure.raw_item_id} label="Open synced run" /></div>
              </li>
            ))}
            {data.risks.map((risk) => (
              <li key={risk} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
                {formatRisk(risk)}
              </li>
            ))}
            {data.risks.length === 0 && data.github_failures.length === 0 && <EmptyLine>No project flags.</EmptyLine>}
          </BriefSection>

          <BriefSection title="Active Ideas" icon={<Lightbulb size={16} />}>
            {data.active_ideas.map((idea) => (
              <li key={idea.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-700">
                {idea.body}
              </li>
            ))}
            {data.active_ideas.length === 0 && <EmptyLine>No active ideas.</EmptyLine>}
          </BriefSection>

          <BriefSection title="Recent Decisions" icon={<FileText size={16} />}>
            {data.recent_decisions.map((decision) => (
              <li key={decision.id} className="rounded-md border border-slate-200 bg-white p-3">
                <div className="font-medium text-slate-900">{decision.title}</div>
                {decision.rationale && <p className="mt-1 text-sm text-slate-600">{decision.rationale}</p>}
              </li>
            ))}
            {data.recent_decisions.length === 0 && <EmptyLine>No decisions yet.</EmptyLine>}
          </BriefSection>

          <BriefSection title="Recent Sources" icon={<FileText size={16} />}>
            {data.recent_sources.map((source) => (
              <li key={source.raw_item_id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
                <SourceLink rawItemId={source.raw_item_id} label={source.title} />
                <div className="mt-1 text-xs text-slate-500">{source.source_type}</div>
              </li>
            ))}
            {data.recent_sources.length === 0 && <EmptyLine>No sources yet.</EmptyLine>}
          </BriefSection>
        </aside>
      </div>
    </section>
  );
}

function CountPill({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="text-lg font-semibold text-slate-950">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function BriefSection({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section>
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
        {icon}
        {title}
      </div>
      <ul className="space-y-2">{children}</ul>
    </section>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return <li className="rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-500">{children}</li>;
}

function formatRisk(risk: string) {
  return risk.replace(/_/g, ' ');
}
