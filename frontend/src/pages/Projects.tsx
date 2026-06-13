import { useQuery } from '@tanstack/react-query';
import { listProjects } from '../api/views';

export default function Projects() {
  const projects = useQuery({ queryKey: ['projects'], queryFn: listProjects });

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4">
      <h1 className="mb-4 text-xl font-semibold">Projects</h1>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {projects.data?.map((project) => (
          <article key={project.id} className="rounded-md border border-slate-200 p-3">
            <h2 className="font-semibold">{project.name}</h2>
            <p className="mt-1 text-sm text-slate-500">{project.description || 'No description yet.'}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
