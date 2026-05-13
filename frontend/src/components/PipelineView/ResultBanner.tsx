import type { PipelineResult } from '../../types'

interface Props {
  result: PipelineResult
}

export function ResultBanner({ result }: Props) {
  return (
    <div className="p-notification--positive">
      <div className="p-notification__content">
        <h5 className="p-notification__title">✅ Pipeline complete</h5>
        <p className="p-notification__message">
          <strong>Charm:</strong> {result.charm_file}<br />
          <strong>Rock:</strong> {result.rock_file}<br />
          <strong>Model:</strong> {result.juju_model}<br />
          <strong>App:</strong> {result.juju_app}
        </p>
      </div>
    </div>
  )
}
