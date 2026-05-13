import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useHistory } from '../hooks/useHistory'
import type { HistoryEntry } from '../types'

const makeEntry = (id: string, label = 'my-repo'): HistoryEntry => ({
  pipeline_id: id,
  label,
  timestamp: new Date().toISOString(),
  status: 'pending',
})

describe('useHistory', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('starts empty when localStorage is empty', () => {
    const { result } = renderHook(() => useHistory())
    expect(result.current.history).toEqual([])
  })

  it('addEntry adds to history', () => {
    const { result } = renderHook(() => useHistory())
    act(() => result.current.addEntry(makeEntry('p1')))
    expect(result.current.history).toHaveLength(1)
    expect(result.current.history[0].pipeline_id).toBe('p1')
  })

  it('addEntry deduplicates by pipeline_id', () => {
    const { result } = renderHook(() => useHistory())
    act(() => {
      result.current.addEntry(makeEntry('p1'))
      result.current.addEntry({ ...makeEntry('p1'), label: 'updated' })
    })
    expect(result.current.history).toHaveLength(1)
    expect(result.current.history[0].label).toBe('updated')
  })

  it('addEntry prepends newest first', () => {
    const { result } = renderHook(() => useHistory())
    act(() => {
      result.current.addEntry(makeEntry('p1'))
      result.current.addEntry(makeEntry('p2'))
    })
    expect(result.current.history[0].pipeline_id).toBe('p2')
    expect(result.current.history[1].pipeline_id).toBe('p1')
  })

  it('persists to localStorage', () => {
    const { result } = renderHook(() => useHistory())
    act(() => result.current.addEntry(makeEntry('p1')))
    const stored = JSON.parse(localStorage.getItem('cs_history') ?? '[]')
    expect(stored).toHaveLength(1)
    expect(stored[0].pipeline_id).toBe('p1')
  })

  it('caps history at 20 entries', () => {
    const { result } = renderHook(() => useHistory())
    act(() => {
      for (let i = 0; i < 25; i++) {
        result.current.addEntry(makeEntry(`p${i}`))
      }
    })
    expect(result.current.history).toHaveLength(20)
  })

  it('updateStatus changes the status of an existing entry', () => {
    const { result } = renderHook(() => useHistory())
    act(() => result.current.addEntry(makeEntry('p1')))
    act(() => result.current.updateStatus('p1', 'done'))
    expect(result.current.history[0].status).toBe('done')
  })

  it('updateStatus is no-op for unknown pipeline_id', () => {
    const { result } = renderHook(() => useHistory())
    act(() => result.current.addEntry(makeEntry('p1')))
    act(() => result.current.updateStatus('unknown', 'failed'))
    expect(result.current.history[0].status).toBe('pending')
  })

  it('hydrates from existing localStorage on mount', () => {
    localStorage.setItem('cs_history', JSON.stringify([makeEntry('pre-existing')]))
    const { result } = renderHook(() => useHistory())
    expect(result.current.history[0].pipeline_id).toBe('pre-existing')
  })
})
