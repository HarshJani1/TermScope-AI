import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { listDocuments, deleteDocument } from '../api/client'
import DocumentCard from '../components/DocumentCard'
import { FileText, RefreshCw, Search } from 'lucide-react'
import './DocumentsPage.css'

const STATUS_FILTERS = ['all', 'completed', 'processing', 'failed']

export default function DocumentsPage() {
  const navigate = useNavigate()
  const [docs, setDocs]     = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  const fetchDocs = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocs(res.data.documents)
    } catch {/* silent */}
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    fetchDocs()
    const id = setInterval(() => {
      setDocs((prev) => {
        const has = prev.some((d) => !['completed','failed'].includes(d.status))
        if (has) fetchDocs()
        return prev
      })
    }, 5000)
    return () => clearInterval(id)
  }, [fetchDocs])

  const handleDelete = async (id) => {
    if (!confirm('Delete this document and all its data?')) return
    try {
      await deleteDocument(id)
      setDocs((prev) => prev.filter((d) => d.id !== id))
    } catch {/* silent */}
  }

  const filtered = docs
    .filter((d) => filter === 'all' || d.status === filter ||
      (['processing','extracting','cleaning','indexing','analyzing'].includes(d.status) && filter === 'processing'))
    .filter((d) => !search || d.filename.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="page-container fade-in">
      <div className="page-header">
        <div>
          <h1 className="page-title">Documents</h1>
          <p className="page-subtitle">{docs.length} document{docs.length !== 1 ? 's' : ''} in your library</p>
        </div>
        <div className="docs-toolbar">
          <button className="btn btn-secondary btn-sm" onClick={fetchDocs}>
            <RefreshCw size={14} />
            Refresh
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/dashboard')}>
            + Upload
          </button>
        </div>
      </div>

      {/* Search + filter bar */}
      <div className="docs-filter-bar">
        <div className="search-wrap">
          <Search size={15} className="search-icon" />
          <input
            className="form-input search-input"
            placeholder="Search documents…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-tabs">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              className={`filter-tab ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <div className="spinner spinner-lg" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><FileText size={28} /></div>
          <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
            {search || filter !== 'all' ? 'No matching documents' : 'No documents yet'}
          </div>
          <div style={{ fontSize: '0.875rem' }}>
            {search || filter !== 'all' ? 'Try adjusting your search or filter' : 'Upload your first document from the Dashboard'}
          </div>
        </div>
      ) : (
        <div className="docs-grid">
          {filtered.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  )
}
