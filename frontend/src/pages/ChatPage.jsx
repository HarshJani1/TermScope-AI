import { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getDocument, getTranscript, askQuestion } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import {
  ArrowLeft, Send, Copy, Download, Bot, User,
  FileText, Clock, CheckCircle2
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import './ChatPage.css'

export default function ChatPage() {
  const { docId } = useParams()
  const navigate  = useNavigate()

  const [doc, setDoc]           = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [sending, setSending]   = useState(false)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [copied, setCopied]     = useState(false)
  const [activeTab, setActiveTab] = useState('chat')  // 'chat' | 'analysis' | 'transcript'

  const bottomRef  = useRef()
  const inputRef   = useRef()
  const pollingRef = useRef()

  const fetchDoc = useCallback(async () => {
    const res = await getDocument(docId)
    setDoc(res.data.document)
    return res.data.document
  }, [docId])

  const fetchMessages = useCallback(async () => {
    const res = await getTranscript(docId)
    setMessages(res.data.messages ?? [])
  }, [docId])

  useEffect(() => {
    const init = async () => {
      try {
        const d = await fetchDoc()
        if (d.status === 'completed') {
          await fetchMessages()
        } else if (!['failed'].includes(d.status)) {
          // Poll until completed
          pollingRef.current = setInterval(async () => {
            const updated = await fetchDoc()
            if (updated.status === 'completed') {
              clearInterval(pollingRef.current)
              await fetchMessages()
            } else if (updated.status === 'failed') {
              clearInterval(pollingRef.current)
            }
          }, 3000)
        }
      } catch {
        setError('Failed to load document.')
      } finally {
        setLoading(false)
      }
    }
    init()
    return () => clearInterval(pollingRef.current)
  }, [fetchDoc, fetchMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleSend = async () => {
    const q = input.trim()
    if (!q || sending) return

    setInput('')
    setSending(true)
    setError('')

    // Optimistic UI
    const optimistic = { id: Date.now(), role: 'user', content: q, created_at: new Date().toISOString() }
    setMessages((prev) => [...prev, optimistic])

    try {
      const res = await askQuestion(docId, q)
      const answer = {
        id: Date.now() + 1,
        role: 'assistant',
        content: res.data.answer,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, answer])
    } catch (err) {
      setError(err.response?.data?.error ?? 'Failed to get a response.')
      // Remove optimistic message on failure
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id))
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const copyTranscript = async () => {
    try {
      const res = await getTranscript(docId)
      await navigator.clipboard.writeText(res.data.transcript_markdown)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {/* silent */}
  }

  const downloadTranscript = async () => {
    try {
      const res = await getTranscript(docId)
      const blob = new Blob([res.data.transcript_markdown], { type: 'text/markdown' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      a.download = `termscope-transcript-doc${docId}.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch {/* silent */}
  }

  const isProcessing = doc && !['completed','failed'].includes(doc.status)

  if (loading) {
    return (
      <div className="chat-loading">
        <div className="spinner spinner-lg" />
        <div className="text-muted" style={{ marginTop: '1rem' }}>Loading document…</div>
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="page-container">
        <div className="alert alert-error">Document not found.</div>
      </div>
    )
  }

  const chatMessages = messages.filter((m) => m.role !== 'system')

  return (
    <div className="chat-layout fade-in">
      {/* Header */}
      <div className="chat-header">
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/documents')}>
          <ArrowLeft size={15} />
          Back
        </button>
        <div className="chat-header-info">
          <div className="chat-doc-name">
            <FileText size={15} />
            {doc.filename}
          </div>
          <StatusBadge status={doc.status} />
        </div>
        <div className="chat-header-actions">
          <button className="btn btn-secondary btn-sm" onClick={copyTranscript}>
            <Copy size={13} />
            {copied ? 'Copied!' : 'Copy'}
          </button>
          <button className="btn btn-secondary btn-sm" onClick={downloadTranscript}>
            <Download size={13} />
            .md
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="chat-tabs">
        {['chat', 'analysis', 'transcript'].map((tab) => (
          <button
            key={tab}
            className={`chat-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Processing notice */}
      {isProcessing && (
        <div className="chat-processing-notice">
          <div className="pulse-dot" />
          <span>
            <strong>{doc.status.charAt(0).toUpperCase() + doc.status.slice(1)}…</strong>
            {' '}AI is analyzing your document. This usually takes 15–60 seconds.
          </span>
          <div className="spinner" style={{ marginLeft: 'auto' }} />
        </div>
      )}

      {doc.status === 'failed' && (
        <div className="alert alert-error" style={{ margin: '0 1.5rem' }}>
          Analysis failed: {doc.error_message}
        </div>
      )}

      {/* ─── TAB: CHAT ─── */}
      {activeTab === 'chat' && (
        <div className="chat-body">
          <div className="chat-messages">
            {/* Initial analysis as first assistant message */}
            {doc.status === 'completed' && doc.llm_response && chatMessages.length === 0 && (
              <div className="chat-msg chat-msg-assistant">
                <div className="chat-msg-avatar bot-avatar"><Bot size={16} /></div>
                <div className="chat-msg-bubble">
                  <div className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {doc.llm_response}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            )}

            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`chat-msg ${msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="chat-msg-avatar bot-avatar"><Bot size={16} /></div>
                )}
                <div className="chat-msg-bubble">
                  {msg.role === 'assistant' ? (
                    <div className="markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="chat-msg-avatar user-avatar"><User size={16} /></div>
                )}
              </div>
            ))}

            {sending && (
              <div className="chat-msg chat-msg-assistant">
                <div className="chat-msg-avatar bot-avatar"><Bot size={16} /></div>
                <div className="chat-msg-bubble chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="chat-input-wrap">
            {error && <div className="alert alert-error" style={{ marginBottom: '0.75rem' }}>{error}</div>}
            <div className="chat-input-row">
              <textarea
                ref={inputRef}
                id="chat-input"
                className="chat-textarea"
                placeholder={
                  doc.status !== 'completed'
                    ? 'Waiting for analysis to complete…'
                    : 'Ask a follow-up question about this document…'
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={doc.status !== 'completed' || sending}
                rows={1}
              />
              <button
                id="chat-send"
                className="btn btn-primary chat-send-btn"
                onClick={handleSend}
                disabled={!input.trim() || doc.status !== 'completed' || sending}
              >
                {sending ? <div className="spinner" /> : <Send size={16} />}
              </button>
            </div>
            <div className="chat-hint">Enter to send · Shift+Enter for new line</div>
          </div>
        </div>
      )}

      {/* ─── TAB: ANALYSIS ─── */}
      {activeTab === 'analysis' && (
        <div className="analysis-panel">
          {doc.status === 'completed' && doc.llm_response ? (
            <div className="card fade-in" style={{ maxWidth: '860px', margin: '0 auto' }}>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{doc.llm_response}</ReactMarkdown>
              </div>
            </div>
          ) : isProcessing ? (
            <div className="empty-state">
              <div className="spinner spinner-lg" />
              <div className="text-muted">Generating analysis…</div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon"><CheckCircle2 size={28} /></div>
              <div>No analysis available</div>
            </div>
          )}
        </div>
      )}

      {/* ─── TAB: TRANSCRIPT ─── */}
      {activeTab === 'transcript' && (
        <div className="transcript-panel">
          <div className="transcript-doc-meta card fade-in" style={{ maxWidth: '860px', margin: '0 auto 1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{doc.filename}</div>
                <div className="text-muted" style={{ fontSize: '0.8125rem', display: 'flex', gap: '1rem' }}>
                  <span><Clock size={12} style={{ verticalAlign: 'middle' }} /> {doc.created_at ? formatDistanceToNow(new Date(doc.created_at), { addSuffix: true }) : '—'}</span>
                  <span>Type: {doc.file_type?.toUpperCase()}</span>
                  <span>Size: {(doc.file_size / 1024).toFixed(1)} KB</span>
                </div>
              </div>
              <StatusBadge status={doc.status} />
            </div>
          </div>
          <div className="card fade-in" style={{ maxWidth: '860px', margin: '0 auto' }}>
            {chatMessages.length === 0 ? (
              <div className="empty-state" style={{ padding: '2rem' }}>
                <div className="text-muted">No follow-up Q&amp;A yet. Start chatting!</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {chatMessages.map((msg) => (
                  <div key={msg.id} className="transcript-entry">
                    <div className={`transcript-role ${msg.role}`}>
                      {msg.role === 'user' ? <User size={13} /> : <Bot size={13} />}
                      {msg.role === 'user' ? 'You' : 'TermScope AI'}
                      <span className="transcript-time">
                        {msg.created_at
                          ? formatDistanceToNow(new Date(msg.created_at), { addSuffix: true })
                          : ''}
                      </span>
                    </div>
                    <div className="markdown-body">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
