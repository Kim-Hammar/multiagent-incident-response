import { useEffect, useRef } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

/**
 * Interactive terminal component using xterm.js over WebSocket.
 */
function Terminal({ containerName, token, onClose }) {
  const termRef = useRef(null)
  const termInstance = useRef(null)
  const wsRef = useRef(null)

  useEffect(() => {
    const term = new XTerm({
      cursorBlink: true,
      fontSize: 13,
      fontFamily: 'monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4'
      }
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(termRef.current)
    fitAddon.fit()
    termInstance.current = term

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl =
      `${protocol}//${window.location.host}` +
      `/api/digital-twin/terminal/${containerName}?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      fitAddon.fit()
      const dims = { type: 'resize', rows: term.rows, cols: term.cols }
      ws.send(JSON.stringify(dims))
    }

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(event.data))
      } else {
        term.write(event.data)
      }
    }

    ws.onclose = () => {
      term.write('\r\n\x1b[90m[Connection closed]\x1b[0m\r\n')
    }

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    const handleResize = () => {
      fitAddon.fit()
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'resize', rows: term.rows, cols: term.cols }))
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      ws.close()
      term.dispose()
    }
  }, [containerName, token])

  return (
    <div className="terminal-wrapper">
      <div className="terminal-header">
        <span className="terminal-title">{containerName}</span>
        <button
          type="button"
          className="btn btn-sm btn-outline-light terminal-close"
          onClick={onClose}
        >
          &times;
        </button>
      </div>
      <div className="terminal-body" ref={termRef} />
    </div>
  )
}

export default Terminal
