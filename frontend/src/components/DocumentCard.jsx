import { useNavigate } from 'react-router-dom'
import { FileText, Image, Trash2, MessageSquare, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import StatusBadge from './StatusBadge'
import './DocumentCard.css'

export default function DocumentCard({ doc, onDelete }) {
  const navigate = useNavigate()
  const isImage = ['png','jpg','jpeg','webp','tiff','gif','bmp'].includes(doc.file_type)
  const FileIcon = isImage ? Image : FileText
  const isReady  = doc.status === 'completed'
  const isFailed = doc.status === 'failed'

  const age = doc.created_at
    ? formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })
    : '—'

  return (
    <div className={`doc-card ${isReady ? 'doc-card-ready' : ''}`}>
      <div className="doc-card-header">
        <div className="doc-icon-wrap">
          <FileIcon size={20} />
        </div>
        <StatusBadge status={doc.status} />
      </div>

      <div className="doc-card-body">
        <div className="doc-name" title={doc.filename}>{doc.filename}</div>
        <div className="doc-meta">
          <span className="badge badge-neutral">{doc.file_type?.toUpperCase()}</span>
          <span className="doc-size">{(doc.file_size / 1024).toFixed(1)} KB</span>
        </div>
        {isFailed && doc.error_message && (
          <div className="doc-error">{doc.error_message}</div>
        )}
      </div>

      <div className="doc-card-footer">
        <span className="doc-age">
          <Clock size={12} />
          {age}
        </span>
        <div className="doc-actions">
          {isReady && (
            <button
              className="btn btn-sm btn-primary"
              onClick={() => navigate(`/chat/${doc.id}`)}
            >
              <MessageSquare size={13} />
              Chat
            </button>
          )}
          <button
            className="btn btn-sm btn-danger btn-icon"
            onClick={() => onDelete(doc.id)}
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
    </div>
  )
}
