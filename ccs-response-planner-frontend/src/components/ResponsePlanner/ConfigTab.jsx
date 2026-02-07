import { useState } from 'react'

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
 * Configuration tab for the response planner — input form with
 * system description, security alerts, and operator input fields.
 */
function ConfigTab({
  systemDescription,
  setSystemDescription,
  securityAlerts,
  setSecurityAlerts,
  operatorFeedback,
  setOperatorFeedback,
  systemDescriptionImages,
  setSystemDescriptionImages,
  securityAlertsImages,
  setSecurityAlertsImages,
  operatorFeedbackImages,
  setOperatorFeedbackImages,
  specification,
  setSpecification,
  specificationImages,
  setSpecificationImages,
  handlePaste,
  fetchExample,
  onClear,
  onGenerate,
  generating
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        onGenerate()
      }}
    >
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
        <ImageThumbnails images={systemDescriptionImages} setImages={setSystemDescriptionImages} />
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
        <label htmlFor="operatorFeedback">Operator input</label>
        <p className="input-hint">
          Optionally provide additional context or instructions for the planner.
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
      <div className="input-section">
        <label htmlFor="specification">Specification</label>
        <p className="input-hint">
          Define constraints the plan must satisfy, e.g., which services must remain accessible.
        </p>
        <textarea
          className="form-control planner-textarea"
          id="specification"
          rows="6"
          placeholder="e.g., Server 1 Nginx must remain accessible from the gateway at all times..."
          value={specification}
          onChange={(e) => setSpecification(e.target.value)}
          onPaste={handlePaste(setSpecificationImages)}
        />
        <ImageThumbnails images={specificationImages} setImages={setSpecificationImages} />
      </div>
      <button type="submit" className="btn btn-dark btn-sm btn-generate" disabled={generating}>
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
        onClick={onClear}
      >
        <i className="fa fa-eraser" aria-hidden="true" /> Clear all
      </button>
    </form>
  )
}

export default ConfigTab
