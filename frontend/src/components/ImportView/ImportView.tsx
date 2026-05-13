import { useState } from 'react'
import { startPipeline } from '../../api/client'
import type { ImportSource } from '../../types'
import { GitTab } from './GitTab'

type TabKey = 'git' | 'bitbucket' | 'url'

interface Props {
  onPipelineStarted: (pipelineId: string, label: string, source: ImportSource) => void
}

export function ImportView({ onPipelineStarted }: Props) {
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('git')

  async function handleSubmit(source: ImportSource, label: string) {
    setLoading(true)
    setErrorMsg(null)
    try {
      const { pipeline_id } = await startPipeline(source)
      onPipelineStarted(pipeline_id, label, source)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'git', label: 'Git' },
    { key: 'bitbucket', label: 'Bitbucket' },
    { key: 'url', label: 'From URL' },
  ]

  return (
    <div className="import-view">
      <h1 className="p-heading--2">Import Project</h1>

      <nav className="p-tabs">
        <ul className="p-tabs__list" role="tablist">
          {tabs.map(tab => (
            <li key={tab.key} className="p-tabs__item" role="presentation">
              <a
                className="p-tabs__link"
                role="tab"
                aria-selected={activeTab === tab.key}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {errorMsg && (
        <div className="p-notification--negative">
          <div className="p-notification__content">
            <p className="p-notification__message">{errorMsg}</p>
          </div>
        </div>
      )}

      {activeTab === 'git' && <GitTab onSubmit={handleSubmit} loading={loading} urlPlaceholder="https://github.com/username/repository" tokenPlaceholder="ghp_xxxxxxxxxxxx" />}
      {activeTab === 'bitbucket' && <GitTab onSubmit={handleSubmit} loading={loading} urlPlaceholder="https://bitbucket.org/workspace/repository" tokenPlaceholder="ATBB_xxxxxxxxxxxx" />}
      {activeTab === 'url' && <GitTab onSubmit={handleSubmit} loading={loading} urlPlaceholder="https://example.com/project/archive.tar.gz" showBranch={false} />}

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
