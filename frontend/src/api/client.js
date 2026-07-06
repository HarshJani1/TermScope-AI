import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('termscope_token')
  console.log(token);
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('termscope_token')
      localStorage.removeItem('termscope_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

/* ── Auth ── */
export const signup = (data) => api.post('/auth/signup', data)
export const login  = (data) => api.post('/auth/login', data)
export const logout = () => api.post('/auth/logout')

/* ── Documents ── */
export const uploadDocument  = (formData) =>
  api.post('/documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
export const listDocuments   = ()        => api.get('/documents')
export const getDocument     = (id)      => api.get(`/documents/${id}`)
export const getDocStatus    = (id)      => api.get(`/documents/${id}/status`)
export const deleteDocument  = (id)      => api.delete(`/documents/${id}`)

/* ── Chat ── */
export const askQuestion     = (docId, question) => api.post(`/chat/${docId}/ask`, { question })
export const getTranscript   = (docId)           => api.get(`/chat/${docId}/transcript`)

/* ── Health ── */
export const healthCheck     = ()        => api.get('/health')

export default api
