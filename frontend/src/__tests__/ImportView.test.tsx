import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import React from 'react'
import { ImportView } from '../components/ImportView/ImportView'

// Mock the API client
vi.mock('../api/client', () => ({
  startPipeline: vi.fn(),
}))

import { startPipeline } from '../api/client'

describe('ImportView', () => {
  const onStarted = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders three tab buttons', () => {
    render(<ImportView onPipelineStarted={onStarted} />)
    expect(screen.getByRole('tab', { name: /git/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /bitbucket/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /direct url/i })).toBeInTheDocument()
  })

  it('shows git tab form by default', () => {
    render(<ImportView onPipelineStarted={onStarted} />)
    expect(screen.getByLabelText(/repository url/i)).toBeInTheDocument()
  })

  it('switches to bitbucket tab on click', () => {
    render(<ImportView onPipelineStarted={onStarted} />)
    fireEvent.click(screen.getByRole('tab', { name: /bitbucket/i }))
    expect(screen.getByLabelText(/workspace/i)).toBeInTheDocument()
  })

  it('switches to url tab on click', () => {
    render(<ImportView onPipelineStarted={onStarted} />)
    fireEvent.click(screen.getByRole('tab', { name: /direct url/i }))
    expect(screen.getByLabelText(/archive url/i)).toBeInTheDocument()
  })

  it('submits git source and calls onPipelineStarted', async () => {
    vi.mocked(startPipeline).mockResolvedValueOnce({ pipeline_id: 'test-123' })

    render(<ImportView onPipelineStarted={onStarted} />)
    fireEvent.change(screen.getByLabelText(/repository url/i), {
      target: { value: 'https://github.com/org/repo.git' },
    })
    fireEvent.click(screen.getByRole('button', { name: /start pipeline/i }))

    await waitFor(() => expect(onStarted).toHaveBeenCalledWith('test-123', 'repo'))
    expect(startPipeline).toHaveBeenCalledWith({
      type: 'git',
      url: 'https://github.com/org/repo.git',
      branch: undefined,
      credentials: undefined,
    })
  })

  it('shows error notification when API call fails', async () => {
    vi.mocked(startPipeline).mockRejectedValueOnce(new Error('Server error'))

    render(<ImportView onPipelineStarted={onStarted} />)
    fireEvent.change(screen.getByLabelText(/repository url/i), {
      target: { value: 'https://github.com/org/repo.git' },
    })
    fireEvent.click(screen.getByRole('button', { name: /start pipeline/i }))

    await waitFor(() => expect(screen.getByText(/server error/i)).toBeInTheDocument())
    expect(onStarted).not.toHaveBeenCalled()
  })
})
