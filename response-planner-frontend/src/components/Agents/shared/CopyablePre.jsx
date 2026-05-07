import { useState } from 'react'

/**
 * A <pre> wrapper with a small copy-to-clipboard icon in the top-right corner.
 * The icon appears on hover and shows a checkmark briefly after copying.
 *
 * @param {string} text - explicit text to copy (falls back to children if omitted)
 * @param {string} className - CSS class(es) for the inner <pre>
 */
function CopyablePre({ children, text, className, ...rest }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e) => {
    e.stopPropagation()
    try {
      const copyText = text !== undefined ? text : typeof children === 'string' ? children : ''
      await navigator.clipboard.writeText(copyText)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard not available */
    }
  }

  return (
    <div className="ia-copyable-block">
      <pre className={className} {...rest}>
        {children}
      </pre>
      <button
        type="button"
        className="ia-copy-btn"
        onClick={handleCopy}
        title={copied ? 'Copied!' : 'Copy to clipboard'}
      >
        <i className={`fa fa-${copied ? 'check' : 'clipboard'}`} aria-hidden="true" />
      </button>
    </div>
  )
}

export default CopyablePre
