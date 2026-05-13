import { useState } from 'react'
import type { ImportSource } from '../../types'

interface Props {
  onSubmit: (source: ImportSource, label: string) => void
  loading: boolean
}

export function UrlTab({ onSubmit, loading }: Props) {
  const [url, setUrl] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!url.trim()) return
    const label = url.split('/').pop() ?? url
    onSubmit({ type: 'url', url: url.trim() }, label)
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="p-form__group">
        <label className="p-form__label" htmlFor="archive-url">Archive URL * (.zip / .tar.gz)</label>
        <input className="p-form__control" id="archive-url" type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com/repo.tar.gz" />
      </div>
      <button className="p-button--positive" type="submit" disabled={loading}>
        {loading ? 'Submitting…' : 'Start pipeline'}
      </button>
    </form>
  )
}
