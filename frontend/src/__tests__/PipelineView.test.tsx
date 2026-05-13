import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'
import { StageCard } from '../components/PipelineView/StageCard'
import { ResultBanner } from '../components/PipelineView/ResultBanner'
import { ErrorBanner } from '../components/PipelineView/ErrorBanner'
import type { Stage } from '../types'

const makeStage = (overrides: Partial<Stage> = {}): Stage => ({
  name: 'verify',
  status: 'pending',
  started_at: null,
  finished_at: null,
  stdout: '',
  stderr: '',
  ...overrides,
})

describe('StageCard', () => {
  it('renders stage name', () => {
    render(<StageCard stage={makeStage({ name: 'verify', status: 'pending' })} />)
    expect(screen.getByText('verify')).toBeInTheDocument()
  })

  it('renders status chip for each status', () => {
    const statuses: Stage['status'][] = ['pending', 'running', 'done', 'failed', 'cancelled']
    for (const status of statuses) {
      const { unmount } = render(<StageCard stage={makeStage({ status })} />)
      expect(screen.getByText(status)).toBeInTheDocument()
      unmount()
    }
  })

  it('shows failed border class when status is failed', () => {
    const { container } = render(<StageCard stage={makeStage({ status: 'failed' })} />)
    expect(container.firstChild).toHaveClass('stage-card--failed')
  })

  it('does not show failed border class when status is done', () => {
    const { container } = render(<StageCard stage={makeStage({ status: 'done' })} />)
    expect(container.firstChild).not.toHaveClass('stage-card--failed')
  })

  it('shows elapsed time when started_at is set', () => {
    const started = new Date(Date.now() - 5000).toISOString()
    render(<StageCard stage={makeStage({ status: 'running', started_at: started })} />)
    expect(screen.getByText(/\ds/)).toBeInTheDocument()
  })

  it('logs are hidden by default', () => {
    render(<StageCard stage={makeStage({ stdout: 'hello world' })} />)
    expect(screen.queryByText('hello world')).not.toBeInTheDocument()
  })

  it('shows logs when Show logs is clicked', () => {
    render(<StageCard stage={makeStage({ stdout: 'hello world' })} />)
    fireEvent.click(screen.getByRole('button', { name: /show logs/i }))
    expect(screen.getByText(/hello world/)).toBeInTheDocument()
  })

  it('hides logs when Hide logs is clicked', () => {
    render(<StageCard stage={makeStage({ stdout: 'hello world' })} />)
    fireEvent.click(screen.getByRole('button', { name: /show logs/i }))
    fireEvent.click(screen.getByRole('button', { name: /hide logs/i }))
    expect(screen.queryByText('hello world')).not.toBeInTheDocument()
  })
})

describe('ResultBanner', () => {
  it('renders all result fields', () => {
    render(
      <ResultBanner
        result={{
          charm_file: '/ws/my.charm',
          rock_file: '/ws/my.rock',
          juju_model: 'model-1',
          juju_app: 'app-1',
        }}
      />
    )
    expect(screen.getByText(/my\.charm/)).toBeInTheDocument()
    expect(screen.getByText(/my\.rock/)).toBeInTheDocument()
    expect(screen.getByText(/model-1/)).toBeInTheDocument()
    expect(screen.getByText(/app-1/)).toBeInTheDocument()
  })
})

describe('ErrorBanner', () => {
  it('renders error message', () => {
    render(<ErrorBanner error="Something went wrong" />)
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
  })
})
