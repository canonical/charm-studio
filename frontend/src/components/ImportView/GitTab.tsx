import { useState } from 'react'
import type { ImportSource } from '../../types'

interface Props {
  onSubmit: (source: ImportSource, label: string) => void
  loading: boolean
}

export function GitTab({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [credentialType, setCredentialType] = useState<'none' | 'pat'>('none')
  const [credentials, setCredentials] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    const label = url.split('/').pop()?.replace(/\.git$/, '') ?? url
    const creds = credentialType === 'pat' && credentials.trim() ? credentials.trim() : undefined
    onSubmit({ url: url.trim(), branch: branch.trim() || undefined, credentials: creds }, label)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="git-url">Repository URL *</label>
        <input
          className="p-form__control"
          id="git-url"
          type="url"
          required
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://github.com/username/repository"
        />
      </div>
      <div className="form-row">
        <div className="p-form__group">
          <label className="p-form__label" htmlFor="git-branch">Branch (optional)</label>
          <input
            className="p-form__control"
            id="git-branch"
            type="text"
            value={branch}
            onChange={e => setBranch(e.target.value)}
            placeholder="main"
          />
        </div>
        <div className="p-form__group">
          <label className="p-form__label" htmlFor="git-cred-type">Credentials (optional)</label>
          <select
            className="p-form__control"
            id="git-cred-type"
            value={credentialType}
            onChange={e => setCredentialType(e.target.value as 'none' | 'pat')}
          >
            <option value="none">None</option>
            <option value="pat">Personal Access Token</option>
          </select>
        </div>
      </div>
      {credentialType === 'pat' && (
        <div className="p-form__group">
          <label className="p-form__label" htmlFor="git-creds">Access Token</label>
          <input
            className="p-form__control"
            id="git-creds"
            type="password"
            value={credentials}
            onChange={e => setCredentials(e.target.value)}
            placeholder="ghp_xxxxxxxxxxxx"
          />
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
        <button className="p-button--positive" type="submit" disabled={loading}>
          {loading ? 'Importing…' : 'Import project'}
        </button>
      </div>
    </form>
  )
}
