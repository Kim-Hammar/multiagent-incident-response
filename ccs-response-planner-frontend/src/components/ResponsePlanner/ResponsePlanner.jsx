import { useState } from 'react'
import { API_EXAMPLE_URL } from '../Common/constants'
import { useAuth } from '../../contexts/AuthContext.jsx'
import './ResponsePlanner.css'

/**
 * Renders a strip of image thumbnails with remove buttons.
 * Clicking a thumbnail opens a full-size lightbox overlay.
 */
function ImageThumbnails({ images, setImages }) {
  const [lightboxSrc, setLightboxSrc] = useState(null)

  if (images.length === 0) return null

  const removeImage = (index) => {
    setImages((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <>
      <div className="image-thumbnails">
        {images.map((src, index) => (
          <div key={index} className="thumbnail-wrapper">
            <img
              src={src}
              alt={`Pasted ${index + 1}`}
              className="thumbnail-img"
              onClick={() => setLightboxSrc(src)}
            />
            <button
              type="button"
              className="thumbnail-remove"
              onClick={() => removeImage(index)}
              aria-label="Remove image"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
      {lightboxSrc && (
        <div className="lightbox-overlay" onClick={() => setLightboxSrc(null)}>
          <button
            type="button"
            className="lightbox-close"
            onClick={() => setLightboxSrc(null)}
            aria-label="Close preview"
          >
            &times;
          </button>
          <img
            src={lightboxSrc}
            alt="Full size preview"
            className="lightbox-img"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  )
}

/**
 * The response planner page component
 */
function ResponsePlanner() {
  const [systemDescription, setSystemDescription] = useState('')
  const [securityAlerts, setSecurityAlerts] = useState('')
  const [operatorFeedback, setOperatorFeedback] = useState('')
  const [systemDescriptionImages, setSystemDescriptionImages] = useState([])
  const [securityAlertsImages, setSecurityAlertsImages] = useState([])
  const [operatorFeedbackImages, setOperatorFeedbackImages] = useState([])
  const { token, logout } = useAuth()

  const handlePaste = (setImages) => (event) => {
    const items = event.clipboardData?.items
    if (!items) return
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        event.preventDefault()
        const file = item.getAsFile()
        const reader = new FileReader()
        reader.onload = (e) => {
          setImages((prev) => [...prev, e.target.result])
        }
        reader.readAsDataURL(file)
      }
    }
  }

  const fetchExample = async () => {
    const res = await fetch(API_EXAMPLE_URL, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.status === 401) {
      logout()
      return
    }
    const data = await res.json()
    setSystemDescription(data.system_description)
    setSecurityAlerts(data.security_alerts)
    setOperatorFeedback(data.operator_feedback)
    setSystemDescriptionImages(data.system_description_images || [])
  }

  return (
    <div className="ResponsePlanner">
      <h2>Response planner</h2>
      <p className="subtitle">
        Provide system details, security alerts, and operator feedback to generate an incident
        response plan.
      </p>
      <hr />
      <form>
        <div className="input-section">
          <label htmlFor="systemDescription">System description</label>
          <p className="input-hint">
            Describe the target system, its architecture, hosts, and services.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="systemDescription"
            rows="8"
            placeholder="e.g., The system consists of a web server (Apache on 10.0.0.1), a database server (PostgreSQL on 10.0.0.2), and a firewall..."
            value={systemDescription}
            onChange={(e) => setSystemDescription(e.target.value)}
            onPaste={handlePaste(setSystemDescriptionImages)}
          />
          <ImageThumbnails
            images={systemDescriptionImages}
            setImages={setSystemDescriptionImages}
          />
        </div>
        <div className="input-section">
          <label htmlFor="securityAlerts">Security alerts and logs</label>
          <p className="input-hint">
            Paste relevant security alerts, IDS logs, or other indicators of compromise.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="securityAlerts"
            rows="8"
            placeholder="e.g., [ALERT] Brute-force SSH login detected on 10.0.0.1 from 192.168.1.50 (200 attempts in 5 min)..."
            value={securityAlerts}
            onChange={(e) => setSecurityAlerts(e.target.value)}
            onPaste={handlePaste(setSecurityAlertsImages)}
          />
          <ImageThumbnails images={securityAlertsImages} setImages={setSecurityAlertsImages} />
        </div>
        <div className="input-section">
          <label htmlFor="operatorFeedback">Operator feedback</label>
          <p className="input-hint">
            Optionally provide feedback to refine a previously generated plan.
          </p>
          <textarea
            className="form-control planner-textarea"
            id="operatorFeedback"
            rows="6"
            placeholder="e.g., The proposed isolation of 10.0.0.1 is not feasible because it hosts a critical customer-facing service..."
            value={operatorFeedback}
            onChange={(e) => setOperatorFeedback(e.target.value)}
            onPaste={handlePaste(setOperatorFeedbackImages)}
          />
          <ImageThumbnails images={operatorFeedbackImages} setImages={setOperatorFeedbackImages} />
        </div>
        <button type="submit" className="btn btn-dark btn-sm btn-generate">
          <i className="fa fa-bolt" aria-hidden="true" /> Generate plan
        </button>
        <button
          type="button"
          className="btn btn-outline-dark btn-sm btn-example"
          onClick={fetchExample}
        >
          <i className="fa fa-download" aria-hidden="true" /> Fetch example incident
        </button>
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm btn-clear"
          onClick={() => {
            setSystemDescription('')
            setSecurityAlerts('')
            setOperatorFeedback('')
            setSystemDescriptionImages([])
            setSecurityAlertsImages([])
            setOperatorFeedbackImages([])
          }}
        >
          <i className="fa fa-eraser" aria-hidden="true" /> Clear all
        </button>
      </form>
    </div>
  )
}

export default ResponsePlanner
