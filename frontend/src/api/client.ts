import type { ImportSource, PipelineStatus } from '../types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function startPipeline(source: ImportSource): Promise<{ pipeline_id: string }> {
  const res = await fetch(`${BASE_URL}/pipeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getPipelineStatus(pipelineId: string): Promise<PipelineStatus> {
  const res = await fetch(`${BASE_URL}/status/${pipelineId}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function cancelPipeline(pipelineId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/pipeline/${pipelineId}`, { method: 'DELETE' })
  if (res.status === 204) return
  const body = await res.json().catch(() => ({}))
  throw new Error((body as { detail?: string }).detail ?? `HTTP ${res.status}`)
}
