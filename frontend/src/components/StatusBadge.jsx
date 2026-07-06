import { Clock, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'

const STATUS_MAP = {
  uploaded:   { label: 'Uploaded',   cls: 'status-uploaded',   icon: Clock },
  processing: { label: 'Processing', cls: 'status-processing', icon: Loader2 },
  extracting: { label: 'Extracting', cls: 'status-extracting', icon: Loader2 },
  cleaning:   { label: 'Cleaning',   cls: 'status-cleaning',   icon: Loader2 },
  indexing:   { label: 'Indexing',   cls: 'status-indexing',   icon: Loader2 },
  analyzing:  { label: 'Analyzing',  cls: 'status-analyzing',  icon: Loader2 },
  completed:  { label: 'Completed',  cls: 'status-completed',  icon: CheckCircle2 },
  failed:     { label: 'Failed',     cls: 'status-failed',     icon: AlertCircle },
}

export default function StatusBadge({ status }) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.uploaded
  const Icon = s.icon
  const isSpinning = ['processing','extracting','cleaning','indexing','analyzing'].includes(status)

  return (
    <span className={`badge ${s.cls}`}>
      <Icon size={11} style={isSpinning ? { animation: 'spin 1s linear infinite' } : {}} />
      {s.label}
    </span>
  )
}
