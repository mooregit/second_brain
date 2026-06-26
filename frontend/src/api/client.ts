export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://secondbrain/api';

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData
      ? options?.headers
      : {
          'Content-Type': 'application/json',
          ...(options?.headers ?? {})
        },
    ...options
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(formatApiError(response.status, detail, response.statusText));
  }
  return response.json() as Promise<T>;
}

function formatApiError(status: number, detail: string, statusText: string): string {
  const parsed = parseJsonDetail(detail);
  if (parsed) return parsed;
  if (status === 413) {
    return 'Upload is too large. The current maximum upload size is 100 MB. For larger PDFs, use the watched inbox folder or raise MAX_UPLOAD_BYTES and nginx client_max_body_size.';
  }
  if (detail.trim().startsWith('<')) return `${status} ${statusText}`;
  return detail || statusText;
}

function parseJsonDetail(detail: string): string | null {
  try {
    const parsed = JSON.parse(detail) as { detail?: unknown };
    if (typeof parsed.detail === 'string') return parsed.detail;
  } catch {
    return null;
  }
  return null;
}
