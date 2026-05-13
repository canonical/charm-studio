import { useState } from 'react'
import type { Stage } from '../../types'
import { LogPanel } from './LogPanel'

interface Props {
  stage: Stage
}

const STATUS_CLASS: Record<string, string> = {
  pending: 'status-chip--pending',
  running: 'status-chip--running',
  done: 'status-chip--done',
  failed: 'status-chip--failed',
  cancelled: 'status-chip--cancelled',
}

function elapsed(stage: Stage): string {
  if (!stage.started_at) return ''
  const end = stage.finished_at ? new Date(stage.finished_at) : new Date()
  const secs = Math.round((end.getTime() - new Date(stage.started_at).getTime()) / 1000)
  const mins = Math.floor(secs / 60)
  const remSecs = secs % 60
  return mins > 0 ? `${mins}:${remSecs.toString().padStart(2, '0')}` : `0:${remSecs.toString().padStart(2, '0')}`
}

export function StageCard({ stage }: Props) {
  const [open, setOpen] = useState(stage.status === 'failed')
  const isFailed = stage.status === 'failed'

  return (
    <div className={`stage-card${isFailed ? ' stage-card--failed' : ''}`}>
      <div className="stage-card__header">
        <span className="stage-card__name">{stage.name}</span>
        <span className={`status-chip ${STATUS_CLASS[stage.status] ?? ''}`}>
          {stage.status}
        </span>
        {stage.started_at && (
          <span className="stage-card__elapsed">⏱ {elapsed(stage)}</span>
        )}
        {(stage.stdout || stage.stderr) && (
          <button
            className="stage-card__toggle"
            onClick={() => setOpen(o => !o)}
          >
            {open ? '▲' : 'View logs ▼'}
          </button>
        )}
      </div>
      {open && (
        <LogPanel
          stdout={stage.stdout}
          stderr={stage.stderr}
          running={stage.status === 'running'}
        />
      )}
    </div>
  )
}
