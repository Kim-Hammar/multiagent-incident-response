import { useState } from 'react'

/**
 * Renders a strip of image thumbnails with remove buttons.
 * Clicking a thumbnail opens a full-size lightbox overlay.
 */
function ImageThumbnails({ images, setImages, disabled }) {
  const [lightboxSrc, setLightboxSrc] = useState(null)

  if (images.length === 0) return null

  const removeImage = (index) => {
    if (disabled) return
    setImages((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <>
      <div className="ia-image-thumbnails">
        {images.map((src, index) => (
          <div key={index} className="ia-thumbnail-wrapper">
            <img
              src={src}
              alt={`Pasted ${index + 1}`}
              className="ia-thumbnail-img"
              onClick={() => setLightboxSrc(src)}
            />
            {!disabled && (
              <button
                type="button"
                className="ia-thumbnail-remove"
                onClick={() => removeImage(index)}
                aria-label="Remove image"
              >
                &times;
              </button>
            )}
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

export default ImageThumbnails
