export type StageStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'
export type StageName = 'verify' | '12factor-charm' | '12factor-rock' | 'deploy'

export interface Stage {
  name: StageName
  status: StageStatus
  started_at: string | null
  finished_at: string | null
  stdout: string
  stderr: string
}

export interface PipelineResult {
  charm_file: string
  rock_file: string
  juju_model: string
  juju_app: string
}

export interface PipelineStatus {
  pipeline_id: string
  done: boolean
  error: string | null
  stages: Stage[]
  result: PipelineResult | null
}

export type HistoryStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'

export interface HistoryEntry {
  pipeline_id: string
  label: string
  timestamp: string
  status: HistoryStatus
}

export interface ImportSource {
  url: string
  branch?: string
  credentials?: string
}
