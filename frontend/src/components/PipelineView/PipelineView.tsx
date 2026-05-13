import { useState } from 'react'
import { cancelPipeline } from '../../api/client'
import type { HistoryStatus } from '../../types'
import { usePipelineStatus } from '../../hooks/usePipelineStatus'
import { StageCard } from './StageCard'
import { ResultBanner } from './ResultBanner'
import { ErrorBanner } from './ErrorBanner'

interface Props {
  pipelineId: string
  onStatusChange: (pipelineId: string, status: HistoryStatus) => void
}

export function PipelineView({ pipelineId, onStatusChange }: Props) {
  const { status, error: fetchError, stopPolling } = usePipelineStatus(pipelineId)
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)
  const [cancelNotice, setCancelNotice] = useState(false)

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

  return (
    <div style={{ padding: '2rem', maxWidth: '800px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <h1 className="p-heading--3" style={{ margin: 0 }}>Pipeline</h1>
        <code style={{ fontSize: '0.8rem', color: '#666' }}>{pipelineId}</code>
        {status && !status.done && (
          <button
            className="p-button--negative u-no-margin--bottom"
            style={{ marginLeft: 'auto' }}
            onClick={handleCancel}
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling…' : 'Cancel pipeline'}
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
          {status.stages.map(stage => (
            <StageCard key={stage.name} stage={stage} />
          ))}
          {status.done && status.error && <ErrorBanner error={status.error} />}
          {status.done && !status.error && status.result && (
            <ResultBanner result={status.result} />
          )}
        </>
      ) : (
        !fetchError && <p>Loading…</p>
      )}
    </div>
  )
}
