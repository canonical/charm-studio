import { useState } from 'react'
import type { Stage } from '../../types'
import { LogPanel } from './LogPanel'

interface Props {
  stage: Stage
}

const STATUS_CHIP: Record<string, string> = {
  pending: '',
  running: 'p-chip--information',
  done: 'p-chip--positive',
  failed: 'p-chip--negative',
  cancelled: 'p-chip--caution',
}

function elapsed(stage: Stage): string {
  if (!stage.started_at) return ''
  const end = stage.finished_at ? new Date(stage.finished_at) : new Date()
  const secs = Math.round((end.getTime() - new Date(stage.started_at).getTime()) / 1000)
  return `${secs}s`
}

export function StageCard({ stage }: Props) {
  const [open, setOpen] = useState(false)
  const isFailed = stage.status === 'failed'

  return (
    <div className={`p-card ${isFailed ? 'stage-card--failed' : ''}`} style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <strong>{stage.name}</strong>
        <span className={`p-chip ${STATUS_CHIP[stage.status] ?? ''}`}>{stage.status}</span>
        {stage.started_at && <small style={{ color: '#666' }}>{elapsed(stage)}</small>}
        <button
          className="p-button--base u-no-margin--bottom"
          style={{ marginLeft: 'auto', fontSize: '0.8rem' }}
          onClick={() => setOpen(o => !o)}
        >
          {open ? 'Hide logs' : 'Show logs'}
        </button>
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
