import { useState } from 'react'
import type { ImportSource } from '../../types'

interface Props {
  onSubmit: (source: ImportSource, label: string) => void
  loading: boolean
}

export function BitbucketTab({ onSubmit, loading }: Props) {
  const [workspace, setWorkspace] = useState('')
  const [repoSlug, setRepoSlug] = useState('')
  const [branch, setBranch] = useState('')
  const [accessToken, setAccessToken] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!workspace.trim() || !repoSlug.trim() || !accessToken.trim()) return
    onSubmit({ type: 'bitbucket', workspace: workspace.trim(), repo_slug: repoSlug.trim(), branch: branch.trim() || undefined, access_token: accessToken.trim() }, `${workspace}/${repoSlug}`)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="bb-workspace">Workspace *</label>
        <input className="p-form__control" id="bb-workspace" type="text" required value={workspace} onChange={e => setWorkspace(e.target.value)} />
      </div>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="bb-slug">Repository slug *</label>
        <input className="p-form__control" id="bb-slug" type="text" required value={repoSlug} onChange={e => setRepoSlug(e.target.value)} />
      </div>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="bb-branch">Branch</label>
        <input className="p-form__control" id="bb-branch" type="text" value={branch} onChange={e => setBranch(e.target.value)} />
      </div>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="bb-token">Access token *</label>
        <input className="p-form__control" id="bb-token" type="password" required value={accessToken} onChange={e => setAccessToken(e.target.value)} />
      </div>
      <button className="p-button--positive" type="submit" disabled={loading}>
        {loading ? 'Submitting…' : 'Start pipeline'}
      </button>
    </form>
  )
}
