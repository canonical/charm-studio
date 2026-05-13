import { useState } from 'react'
import type { ImportSource } from '../../types'

interface Props {
  onSubmit: (source: ImportSource, label: string) => void
  loading: boolean
}

export function GitTab({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [credentials, setCredentials] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    const label = url.split('/').pop()?.replace(/\.git$/, '') ?? url
    onSubmit({ type: 'git', url: url.trim(), branch: branch.trim() || undefined, credentials: credentials.trim() || undefined }, label)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="git-url">Repository URL *</label>
        <input className="p-form__control" id="git-url" type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/org/repo.git" />
      </div>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="git-branch">Branch</label>
        <input className="p-form__control" id="git-branch" type="text" value={branch} onChange={e => setBranch(e.target.value)} placeholder="main" />
      </div>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="git-creds">Credentials (PAT)</label>
        <input className="p-form__control" id="git-creds" type="password" value={credentials} onChange={e => setCredentials(e.target.value)} />
      </div>
      <button className="p-button--positive" type="submit" disabled={loading}>
        {loading ? 'Submitting…' : 'Start pipeline'}
      </button>
    </form>
  )
}
