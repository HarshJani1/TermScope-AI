import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { listDocuments, uploadDocument, deleteDocument } from '../api/client'
import DropZone from '../components/DropZone'
import DocumentCard from '../components/DocumentCard'
import {
  FileText, CheckCircle2, Clock,
  RefreshCw, AlertCircle, ShieldCheck, ArrowUpRight
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
    const timer = window.setTimeout(fetchDocs, 0)
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
    return () => {
      window.clearTimeout(timer)
      clearInterval(id)
    }
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

  const total     = docs.length
  const completed = docs.filter((d) => d.status === 'completed').length
  const processing = docs.filter((d) => !['completed','failed'].includes(d.status)).length
  const failed    = docs.filter((d) => d.status === 'failed').length
  const latestDoc = docs[0]

  const metrics = [
    { label: 'Documents', value: total, icon: FileText },
    { label: 'Analyzed', value: completed, icon: CheckCircle2 },
    { label: 'In review', value: processing, icon: Clock },
    { label: 'Needs attention', value: failed, icon: AlertCircle },
  ]

  return (
    <div className="dashboard-shell fade-in">
      <header className="dashboard-header">
        <div className="dashboard-kicker">
          <ShieldCheck size={14} />
          Terms workspace
        </div>
        <div className="dashboard-title-row">
          <div>
            <h1 className="dashboard-title">Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {user?.username}</h1>
            <p className="dashboard-subtitle">Review dense terms documents without letting the important clauses disappear into the margins.</p>
          </div>
          <button className="btn btn-secondary dashboard-refresh" onClick={fetchDocs} title="Refresh">
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
      </header>

      <section className="dashboard-overview" aria-label="Workspace overview">
        <div className="overview-panel">
          <div className="overview-copy">
            <span className="panel-label">Current read</span>
            <h2>{latestDoc?.filename ?? 'No document selected'}</h2>
            <p>{latestDoc ? 'Latest upload is ready in the queue. Open completed analyses from the document shelf below.' : 'Start by adding a PDF or screenshot of the terms you want to inspect.'}</p>
          </div>
          <div className="overview-mark">
            <FileText size={22} />
          </div>
        </div>

        <div className="metrics-strip">
          {metrics.map(({ label, value, icon: Icon }) => (
            <div className="metric" key={label}>
              <div className="metric-top">
                <Icon size={15} />
                <span>{label}</span>
              </div>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="dashboard-grid">
        <section className="intake-panel">
          <div className="section-heading">
            <div>
              <span className="panel-label">Intake</span>
              <h2>Analyze a terms document</h2>
            </div>
          </div>
        {uploadError   && <div className="alert alert-error"   style={{ marginBottom: '1rem' }}>{uploadError}</div>}
        {uploadSuccess && <div className="alert alert-success" style={{ marginBottom: '1rem' }}>{uploadSuccess}</div>}
        <DropZone onUpload={handleUpload} uploading={uploading} />
      </section>

        <aside className="review-panel">
          <span className="panel-label">Review rhythm</span>
          <div className="review-steps">
            <div className="review-step active">
              <span>01</span>
              <div>
                <strong>Upload</strong>
                <p>PDF or image, up to 16 MB.</p>
              </div>
            </div>
            <div className="review-step">
              <span>02</span>
              <div>
                <strong>Extract</strong>
                <p>Clauses, obligations, and risk signals.</p>
              </div>
            </div>
            <div className="review-step">
              <span>03</span>
              <div>
                <strong>Discuss</strong>
                <p>Ask focused questions against the source.</p>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <section className="documents-panel">
        <div className="section-heading documents-heading">
          <div>
            <span className="panel-label">Library</span>
            <h2>Documents</h2>
          </div>
          {docs.length > 0 && (
            <button className="quiet-link" onClick={() => navigate('/documents')}>
              View all
              <ArrowUpRight size={14} />
            </button>
          )}
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner spinner-lg" />
          </div>
        ) : docs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><FileText size={26} /></div>
            <div style={{ fontWeight: 650, color: 'var(--text-primary)' }}>No documents yet</div>
            <div style={{ fontSize: '0.875rem' }}>Your analyzed terms will appear here.</div>
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
