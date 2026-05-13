import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cancelPipeline } from '../../api/client'
import type { HistoryStatus } from '../../types'
import { usePipelineStatus } from '../../hooks/usePipelineStatus'
import { StageCard } from './StageCard'
import { ResultBanner } from './ResultBanner'
import { ErrorBanner } from './ErrorBanner'

interface Props {
  pipelineId: string
  onStatusChange: (pipelineId: string, status: HistoryStatus) => void
  onRetry?: () => void
}

export function PipelineView({ pipelineId, onStatusChange, onRetry }: Props) {
  const { status, error: fetchError, stopPolling } = usePipelineStatus(pipelineId)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const [cancelNotice, setCancelNotice] = useState(false)
  const navigate = useNavigate()

  // Sync history status when done
  if (status?.done) {
    const hs: HistoryStatus = status.error ? 'failed' : 'done'
    onStatusChange(pipelineId, hs)
  }

  async function handleCancel() {
    setCancelling(true)
    setCancelError(null)
    try {
      await cancelPipeline(pipelineId)
      stopPolling()
      setCancelNotice(true)
      onStatusChange(pipelineId, 'cancelled')
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : String(err))
    } finally {
      setCancelling(false)
    }
  }

  const isRunning = status && !status.done && !cancelNotice
  const isDone = status?.done && !status.error
  const isFailed = status?.done && !!status.error
  const deployStarted = status?.stages.some(s => s.name === 'deploy' && (s.status === 'running' || s.status === 'done')) ?? false
  const deploySucceeded = status?.stages.some(s => s.name === 'deploy' && s.status === 'done') ?? false

  return (
    <div>
      <div className="pipeline-header">
        <h1 className="pipeline-header__title">Pipeline Progress</h1>
        {isRunning && (
          <button
            className="p-button--negative u-no-margin--bottom"
            onClick={handleCancel}
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling…' : 'Cancel pipeline'}
          </button>
        )}
        {isFailed && (
          <button
            className="p-button--negative u-no-margin--bottom"
            onClick={onRetry ?? (() => navigate('/'))}
          >
            Retry
          </button>
        )}
        {isDone && (
          <button className="p-button--positive u-no-margin--bottom">
            New Pipeline
          </button>
        )}
      </div>

      {cancelNotice && (
        <div className="p-notification--caution" style={{ marginBottom: '1rem' }}>
          <div className="p-notification__content">
            <p className="p-notification__message">
              Pipeline cancelled. Partially completed stages are preserved in the log.
            </p>
          </div>
        </div>
      )}

      {cancelError && (
        <div className="p-notification--negative" style={{ marginBottom: '1rem' }}>
          <div className="p-notification__content">
            <p className="p-notification__message">{cancelError}</p>
          </div>
        </div>
      )}

      {fetchError && !status && (
        <div className="p-notification--negative">
          <div className="p-notification__content">
            <p className="p-notification__message">{fetchError}</p>
          </div>
        </div>
      )}

      {status ? (
        <>
          {status.done && status.error && <ErrorBanner error={status.error} />}
          {status.done && !status.error && status.result && (
            <ResultBanner result={status.result} />
          )}
          {status.stages.map(stage => (
            <StageCard key={stage.name} stage={stage} />
          ))}
        </>
      ) : (
        !fetchError && <p>Loading…</p>
      )}

      <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
        <a
          className={`p-button--positive u-no-margin--bottom${deployStarted ? '' : ' is-disabled'}`}
          href={deployStarted ? `http://magician.charmhub.studio/admin/${pipelineId}` : undefined}
          target="_blank"
          rel="noopener noreferrer"
          aria-disabled={!deployStarted}
        >
          Visualize Deployment
        </a>
        <a
          className={`p-button u-no-margin--bottom${deploySucceeded ? '' : ' is-disabled'}`}
          href={deploySucceeded ? `https://${pipelineId}.charmhub.studio` : undefined}
          target="_blank"
          rel="noopener noreferrer"
          aria-disabled={!deploySucceeded}
        >
          Open Project URL
        </a>
      </div>
    </div>
  )
}
