/**
 * Resolve the backend base URL from the Vite env var.
 * - Development: VITE_API_BASE is empty, Vite's dev proxy handles /api/* → localhost:8000
 * - Production:  VITE_API_BASE="https://your-backend.onrender.com" (no trailing slash)
 */
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? ''
const API = `${API_BASE}/api`

export interface UploadResponse {
  success: boolean;
  case_id: string;
  processing_time_seconds: number;
  knowledge_graph: {
    available: boolean;
    nodes: number;
    edges: number;
    entity_types: Record<string, number>;
  };
}

export async function uploadDocuments(
  files: File[],
  token?: string
): Promise<UploadResponse> {

  const formData = new FormData();

  files.forEach(file => {
    formData.append("files", file);
  });

  const response = await fetch(
    `${API}/upload`,
    {
      method: "POST",
      headers: token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : undefined,
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(
      await response.text()
    );
  }

  return response.json();
}