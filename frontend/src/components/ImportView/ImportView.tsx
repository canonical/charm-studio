import { useState } from 'react'
import { startPipeline } from '../../api/client'
import type { ImportSource } from '../../types'
import { GitTab } from './GitTab'
import { BitbucketTab } from './BitbucketTab'
import { UrlTab } from './UrlTab'

interface Props {
  onPipelineStarted: (pipelineId: string, label: string) => void
}

type Tab = 'git' | 'bitbucket' | 'url'

export function ImportView({ onPipelineStarted }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('git')
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
    <div style={{ padding: '2rem', maxWidth: '640px' }}>
      <h1 className="p-heading--2">Import a project</h1>

      {errorMsg && (
        <div className="p-notification--negative">
          <div className="p-notification__content">
            <p className="p-notification__message">{errorMsg}</p>
          </div>
        </div>
      )}

      <div className="p-tabs">
        <ul className="p-tabs__list" role="tablist">
          {(['git', 'bitbucket', 'url'] as Tab[]).map(tab => (
            <li key={tab} className="p-tabs__item" role="presentation">
              <button
                className={`p-tabs__link${activeTab === tab ? ' is-selected' : ''}`}
                role="tab"
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'git' ? 'Git' : tab === 'bitbucket' ? 'Bitbucket' : 'Direct URL'}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        {activeTab === 'git' && <GitTab onSubmit={handleSubmit} loading={loading} />}
        {activeTab === 'bitbucket' && <BitbucketTab onSubmit={handleSubmit} loading={loading} />}
        {activeTab === 'url' && <UrlTab onSubmit={handleSubmit} loading={loading} />}
      </div>
    </div>
  )
}
