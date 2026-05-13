import { useEffect, useRef } from 'react'

interface Props {
  stdout: string
  stderr: string
  running: boolean
}

export function LogPanel({ stdout, stderr, running }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (running && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [stdout, stderr, running])

  return (
    <div className="log-panel" ref={ref}>
      <pre>
        {stdout && <span className="log-stdout">{stdout}</span>}
        {stderr && <span className="log-stderr">{stderr}</span>}
        {!stdout && !stderr && <span className="log-stdout">(no output)</span>}
      </pre>
    </div>
  )
}
