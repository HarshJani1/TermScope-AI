import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { listDocuments, uploadDocument, deleteDocument } from '../api/client'
import DropZone from '../components/DropZone'
import DocumentCard from '../components/DocumentCard'
import {
  LayoutDashboard, FileText, CheckCircle2, Clock,
  RefreshCw, AlertCircle
} from 'lucide-react'
import './Dashboard.css'

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [docs, setDocs]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState('')

  const fetchDocs = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocs(res.data.documents)
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocs()
    // Poll every 5s for processing docs
    const id = setInterval(() => {
      setDocs((prev) => {
        const hasProcessing = prev.some(
          (d) => !['completed','failed'].includes(d.status)
        )
        if (hasProcessing) fetchDocs()
        return prev
      })
    }, 5000)
    return () => clearInterval(id)
  }, [fetchDocs])

  const handleUpload = async (file) => {
    setUploading(true)
    setUploadError('')
    setUploadSuccess('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      await uploadDocument(fd)
      setUploadSuccess('File uploaded! Analysis started in the background.')
      fetchDocs()
    } catch (err) {
      setUploadError(err.response?.data?.error ?? 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this document and all its data?')) return
    try {
      await deleteDocument(id)
      setDocs((prev) => prev.filter((d) => d.id !== id))
    } catch {/* silent */}
  }

  // Stats
  const total     = docs.length
  const completed = docs.filter((d) => d.status === 'completed').length
  const processing = docs.filter((d) => !['completed','failed'].includes(d.status)).length
  const failed    = docs.filter((d) => d.status === 'failed').length

  return (
    <div className="page-container fade-in">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">
            <span className="gradient-text">Welcome, {user?.username}</span>
          </h1>
          <p className="page-subtitle">Upload a Terms &amp; Conditions document to get your AI analysis</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchDocs}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* Stats row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon stat-icon-blue"><FileText size={18} /></div>
          <div>
            <div className="stat-value">{total}</div>
            <div className="stat-label">Total Documents</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stat-icon-green"><CheckCircle2 size={18} /></div>
          <div>
            <div className="stat-value">{completed}</div>
            <div className="stat-label">Analyzed</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stat-icon-amber"><Clock size={18} /></div>
          <div>
            <div className="stat-value">{processing}</div>
            <div className="stat-label">Processing</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon stat-icon-red"><AlertCircle size={18} /></div>
          <div>
            <div className="stat-value">{failed}</div>
            <div className="stat-label">Failed</div>
          </div>
        </div>
      </div>

      {/* Upload section */}
      <section className="section">
        <h2 className="section-title">
          <LayoutDashboard size={18} />
          Upload Document
        </h2>
        {uploadError   && <div className="alert alert-error"   style={{ marginBottom: '1rem' }}>{uploadError}</div>}
        {uploadSuccess && <div className="alert alert-success" style={{ marginBottom: '1rem' }}>{uploadSuccess}</div>}
        <DropZone onUpload={handleUpload} uploading={uploading} />
      </section>

      {/* Documents grid */}
      <section className="section">
        <h2 className="section-title">
          <FileText size={18} />
          Your Documents
        </h2>

        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
            <div className="spinner spinner-lg" />
          </div>
        ) : docs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><FileText size={26} /></div>
            <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>No documents yet</div>
            <div style={{ fontSize: '0.875rem' }}>Upload your first Terms &amp; Conditions document above</div>
          </div>
        ) : (
          <div className="docs-grid">
            {docs.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
