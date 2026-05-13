interface Props {
  error: string
}

export function ErrorBanner({ error }: Props) {
  return (
    <div className="error-banner">
      <span className="error-banner__icon">⊘</span>
      <div className="error-banner__content">
        <h4>Pipeline failed</h4>
        <p>{error}</p>
      </div>
    </div>
  )
}
