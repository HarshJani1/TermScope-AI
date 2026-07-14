import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { signup } from '../api/client'
import './Auth.css'

export default function SignupPage() {
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' })
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn } = useAuth()
  const navigate = useNavigate()

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await signup({
        username: form.username,
        email: form.email,
        password: form.password,
      })
      // Auto-login after signup — need to call login endpoint for token
      const { login } = await import('../api/client')
      const loginRes = await login({ email: form.email, password: form.password })
      signIn(loginRes.data.user, loginRes.data.token)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.error ?? 'Signup failed. Please try again.')
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
        {/* Brand */}
        <div className="auth-brand">
          <div className="auth-logo">
            TS
          </div>
          <div>
            <div className="auth-logo-title">TermScope</div>
            <div className="auth-logo-sub">AI Document Analyst</div>
          </div>
        </div>

        <h1 className="auth-heading">Create your account</h1>
        <p className="auth-subheading">Start analyzing legal documents with AI</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label className="form-label">Username</label>
            <div className="input-icon-wrap">
              <input
                id="signup-username"
                className="form-input"
                placeholder="johndoe"
                value={form.username}
                onChange={set('username')}
                required
                minLength={3}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <div className="input-icon-wrap">
              <input
                id="signup-email"
                type="email"
                className="form-input"
                placeholder="john@example.com"
                value={form.email}
                onChange={set('email')}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <div className="input-icon-wrap">
              <input
                id="signup-password"
                type={showPw ? 'text' : 'password'}
                className="form-input input-with-toggle"
                placeholder="Min. 6 characters"
                value={form.password}
                onChange={set('password')}
                required
                minLength={6}
              />
              <button
                type="button"
                className="input-toggle"
                onClick={() => setShowPw((s) => !s)}
              >
                {showPw ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Confirm Password</label>
            <div className="input-icon-wrap">
              <input
                id="signup-confirm"
                type={showPw ? 'text' : 'password'}
                className="form-input"
                placeholder="Repeat password"
                value={form.confirm}
                onChange={set('confirm')}
                required
              />
            </div>
          </div>

          <button
            id="signup-submit"
            type="submit"
            className="btn btn-primary btn-lg auth-submit"
            disabled={loading}
          >
            {loading ? <><div className="spinner" />Creating account…</> : 'Create Account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
