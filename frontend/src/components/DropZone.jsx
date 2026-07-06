import { useState, useRef, useCallback } from 'react'
import { Upload, FileText, Image, X } from 'lucide-react'
import './DropZone.css'

const ALLOWED = {
  'application/pdf': 'pdf',
  'image/png': 'image', 'image/jpeg': 'image',
  'image/jpg': 'image', 'image/webp': 'image',
  'image/tiff': 'image', 'image/gif': 'image',
}

export default function DropZone({ onUpload, uploading }) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [error, setError] = useState('')
  const inputRef = useRef()

  const validate = (file) => {
    if (!ALLOWED[file.type]) {
      setError('Only PDF and image files (PNG, JPG, WEBP, TIFF) are allowed.')
      return false
    }
    if (file.size > 16 * 1024 * 1024) {
      setError('File must be under 16 MB.')
      return false
    }
    return true
  }

  const handleFile = useCallback((file) => {
    setError('')
    if (validate(file)) setSelectedFile(file)
  }, [])

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleChange = (e) => {
    const file = e.target.files[0]
    if (file) handleFile(file)
  }

  const handleSubmit = () => {
    if (!selectedFile) return
    onUpload(selectedFile)
    setSelectedFile(null)
  }

  const fileType = selectedFile ? ALLOWED[selectedFile.type] : null
  const FileIcon = fileType === 'pdf' ? FileText : Image

  return (
    <div className="dropzone-wrapper">
      {!selectedFile ? (
        <>
          <div
            className={`dropzone ${dragOver ? 'drag-over' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <div className="dropzone-icon">
              <Upload size={26} />
            </div>
            <div className="dropzone-title">Drop your file here</div>
            <div className="dropzone-subtitle">or click to browse your computer</div>
            <div className="dropzone-btn">
              <Upload size={14} />
              Browse Files
            </div>
            <div className="dropzone-types">PDF, PNG, JPG, WEBP, TIFF · Max 16 MB</div>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff,.gif"
            style={{ display: 'none' }}
            onChange={handleChange}
          />
          {error && (
            <div className="alert alert-error" style={{ marginTop: '0.75rem' }}>
              {error}
            </div>
          )}
        </>
      ) : (
        <div className="upload-progress">
          <div className="upload-progress-header">
            <div className="upload-progress-name">
              <FileIcon size={16} style={{ color: 'var(--accent)' }} />
              {selectedFile.name}
            </div>
            {!uploading && (
              <button
                className="btn btn-ghost btn-icon"
                onClick={() => setSelectedFile(null)}
              >
                <X size={14} />
              </button>
            )}
          </div>
          <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · {fileType?.toUpperCase()}
          </div>
          {uploading ? (
            <div>
              <div className="progress-bar progress-indeterminate">
                <div className="progress-fill" />
              </div>
              <div className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                Uploading and starting analysis...
              </div>
            </div>
          ) : (
            <button className="btn btn-primary" onClick={handleSubmit}>
              <Upload size={15} />
              Analyze Document
            </button>
          )}
        </div>
      )}
    </div>
  )
}
