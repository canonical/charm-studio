import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { usePipelineStatus } from '../hooks/usePipelineStatus'
import type { PipelineStatus } from '../types'

const mockStatus = (done = false): PipelineStatus => ({
  pipeline_id: 'abc',
  done,
  error: null,
  stages: [
    { name: 'verify', status: 'done', started_at: null, finished_at: null, stdout: '', stderr: '' },
    { name: '12factor-charm', status: done ? 'done' : 'running', started_at: null, finished_at: null, stdout: '', stderr: '' },
    { name: '12factor-rock', status: done ? 'done' : 'running', started_at: null, finished_at: null, stdout: '', stderr: '' },
    { name: 'deploy', status: 'pending', started_at: null, finished_at: null, stdout: '', stderr: '' },
  ],
  result: null,
})

const makeFetchOk = (data: unknown) =>
  Promise.resolve({ ok: true, json: async () => data } as Response)

const makeFetchError = (status: number) =>
  Promise.resolve({ ok: false, status } as Response)

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('usePipelineStatus', () => {
  it('returns null status when pipelineId is null', () => {
    const { result } = renderHook(() => usePipelineStatus(null))
    expect(result.current.status).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('fetches status on mount', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(makeFetchOk(mockStatus(false))))

    const { result } = renderHook(() => usePipelineStatus('abc'))
    await waitFor(() => expect(result.current.status).not.toBeNull())

    expect(result.current.status?.pipeline_id).toBe('abc')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/status/abc'),
      expect.anything(),
    )
  })

  it('polls multiple times while not done', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockReturnValue(makeFetchOk(mockStatus(false)))
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => usePipelineStatus('abc'))
    // flush initial poll
    await act(async () => { await Promise.resolve() })
    const callsAfterFirst = fetchMock.mock.calls.length

    // advance past two poll intervals
    await act(async () => { vi.advanceTimersByTime(4100) })
    await act(async () => { await Promise.resolve() })

    expect(fetchMock.mock.calls.length).toBeGreaterThan(callsAfterFirst)
  })

  it('stops polling when done is true', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn().mockReturnValue(makeFetchOk(mockStatus(true)))
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => usePipelineStatus('abc'))
    await act(async () => { await Promise.resolve() })
    await act(async () => { await Promise.resolve() })

    const callsWhenDone = fetchMock.mock.calls.length
    await act(async () => { vi.advanceTimersByTime(6000) })
    await act(async () => { await Promise.resolve() })

    expect(fetchMock.mock.calls.length).toBe(callsWhenDone)
    expect(result.current.status?.done).toBe(true)
  })

  it('sets error on fetch failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(makeFetchError(500)))

    const { result } = renderHook(() => usePipelineStatus('abc'))
    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(result.current.error).toContain('500')
  })

  it('resets status when pipelineId changes to null', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(makeFetchOk(mockStatus(false))))

    const { result, rerender } = renderHook(
      (id: string | null) => usePipelineStatus(id),
      { initialProps: 'abc' as string | null }
    )
    await waitFor(() => expect(result.current.status).not.toBeNull())

    rerender(null)
    expect(result.current.status).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
