import { Link } from 'react-router-dom';

export default function SourceLink({ rawItemId, label }: { rawItemId: string | null; label: string }) {
  if (!rawItemId) return <span>{label}</span>;
  return (
    <Link className="text-sky-700 underline-offset-2 hover:underline" to={`/items/${rawItemId}`}>
      {label}
    </Link>
  );
}

