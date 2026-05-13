import { useEffect, useRef } from 'react'

interface Props {
  stdout: string
  stderr: string
  running: boolean
}

export function LogPanel({ stdout, stderr, running }: Props) {
  const ref = useRef<HTMLPreElement>(null)

  useEffect(() => {
    if (running && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [stdout, stderr, running])

  const content = [stdout, stderr].filter(Boolean).join('\n--- stderr ---\n')

  return (
    <div className="stage-log">
      <pre ref={ref}>{content || '(no output)'}</pre>
    </div>
  )
}
