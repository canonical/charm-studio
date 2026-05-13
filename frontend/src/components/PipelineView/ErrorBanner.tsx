interface Props {
  error: string
}

export function ErrorBanner({ error }: Props) {
  return (
    <div className="p-notification--negative">
      <div className="p-notification__content">
        <h5 className="p-notification__title">Pipeline failed</h5>
        <p className="p-notification__message">{error}</p>
      </div>
    </div>
  )
}
