import { useState } from 'react'
import { startPipeline } from '../../api/client'
import type { ImportSource } from '../../types'
import { GitTab } from './GitTab'

interface Props {
  onPipelineStarted: (pipelineId: string, label: string) => void
}

export function ImportView({ onPipelineStarted }: Props) {
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  async function handleSubmit(source: ImportSource, label: string) {
    setLoading(true)
    setErrorMsg(null)
    try {
      const { pipeline_id } = await startPipeline(source)
      onPipelineStarted(pipeline_id, label)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="import-view">
      <h1 className="p-heading--2">Import Project</h1>

      {errorMsg && (
        <div className="p-notification--negative">
          <div className="p-notification__content">
            <p className="p-notification__message">{errorMsg}</p>
          </div>
        </div>
      )}

      <GitTab onSubmit={handleSubmit} loading={loading} />

      <div className="import-view__info">
        <span>ℹ</span>
        <span>
          Ensure your repository is accessible by Charm Studio. Private repositories may require credentials
          configuration in <strong>Settings</strong>.
        </span>
      </div>
    </div>
  )
}
