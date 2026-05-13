import { useEffect, useMemo, useRef } from 'react'
import { AnsiUp } from 'ansi_up'

interface Props {
  stdout: string
  stderr: string
  running: boolean
}

export function LogPanel({ stdout, stderr, running }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const ansi = useMemo(() => new AnsiUp(), [])

  useEffect(() => {
    if (running && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [stdout, stderr, running])

  return (
    <div className="log-panel" ref={ref}>
      <pre>
        {stdout && (
          <span
            className="log-stdout"
            dangerouslySetInnerHTML={{ __html: ansi.ansi_to_html(stdout) }}
          />
        )}
        {stderr && (
          <span
            className="log-stderr"
            dangerouslySetInnerHTML={{ __html: ansi.ansi_to_html(stderr) }}
          />
        )}
        {!stdout && !stderr && <span className="log-stdout">(no output)</span>}
      </pre>
    </div>
  )
}
