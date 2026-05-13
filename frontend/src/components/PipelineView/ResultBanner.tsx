import type { PipelineResult } from '../../types'

interface Props {
  result: PipelineResult
}

export function ResultBanner({ result }: Props) {
  return (
    <div className="result-banner">
      <div className="result-banner__title">
        <span>✅</span> Pipeline complete
      </div>
      <div className="result-banner__grid">
        <div className="result-banner__item">
          <label>Charm</label>
          <span>{result.charm_file}</span>
        </div>
        <div className="result-banner__item">
          <label>Rock</label>
          <span>{result.rock_file}</span>
        </div>
        <div className="result-banner__item">
          <label>Model</label>
          <span>{result.juju_model}</span>
        </div>
        <div className="result-banner__item">
          <label>App</label>
          <span>{result.juju_app}</span>
        </div>
      </div>
    </div>
  )
}
