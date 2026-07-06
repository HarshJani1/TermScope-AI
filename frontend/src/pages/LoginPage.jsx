import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login } from '../api/client'
import { ShieldCheck, Eye, EyeOff, Mail, Lock, ArrowRight } from 'lucide-react'
import './Auth.css'

export default function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(form)
      signIn(res.data.user, res.data.token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.error ?? 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-bg">
        <div className="auth-glow auth-glow-1" />
        <div className="auth-glow auth-glow-2" />
      </div>

      <div className="auth-card fade-in">
        <div className="auth-brand">
          <div className="auth-logo">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="auth-logo-title">TermScope</div>
            <div className="auth-logo-sub">AI Document Analyst</div>
          </div>
        </div>

        <h1 className="auth-heading">Welcome back</h1>
        <p className="auth-subheading">Sign in to continue your document analysis</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label className="form-label">Email</label>
            <div className="input-icon-wrap">
              <Mail size={15} className="input-icon" />
              <input
                id="login-email"
                type="email"
                className="form-input input-with-icon"
                placeholder="john@example.com"
                value={form.email}
                onChange={set('email')}
                required
                autoFocus
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div className="input-icon-wrap">
              <Lock size={15} className="input-icon" />
              <input
                id="login-password"
                type={showPw ? 'text' : 'password'}
                className="form-input input-with-icon input-with-toggle"
                placeholder="Your password"
                value={form.password}
                onChange={set('password')}
                required
              />
              <button
                type="button"
                className="input-toggle"
                onClick={() => setShowPw((s) => !s)}
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button
            id="login-submit"
            type="submit"
            className="btn btn-primary btn-lg auth-submit"
            disabled={loading}
          >
            {loading ? <><div className="spinner" />Signing in…</> : <>Sign In <ArrowRight size={16} /></>}
          </button>
        </form>

        <p className="auth-switch">
          Don't have an account? <Link to="/signup">Create one</Link>
        </p>
      </div>
    </div>
  )
}
