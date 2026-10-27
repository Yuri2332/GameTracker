import { useEffect } from 'react'
import { Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, BarChart3, BookOpen, ChevronDown, CircleHelp, Gamepad2, Goal as GoalIcon, LayoutDashboard, LogOut, Settings, UserRound, Zap } from 'lucide-react'
import { toast } from 'sonner'
import { api, ensureCsrf } from './lib/api'
import type { User } from './types'
import { Button, LoadingState } from './components/Primitives'
import AuthPage from './pages/AuthPage'
import DashboardPage from './pages/DashboardPage'
import LibraryPage from './pages/LibraryPage'
import GamePage from './pages/GamePage'
import SessionsPage from './pages/SessionsPage'
import GoalsPage from './pages/GoalsPage'
import StatisticsPage from './pages/StatisticsPage'
import IntegrationsPage from './pages/IntegrationsPage'
import SettingsPage from './pages/SettingsPage'
import NotFoundPage from './pages/NotFoundPage'

function Shell({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { data: preferences } = useQuery({ queryKey: ['settings'], queryFn: () => api<{ theme: string; timezone: string }>('/settings') })
  useEffect(() => { if (preferences) { document.documentElement.dataset.theme = preferences.theme; document.documentElement.dataset.timezone = preferences.timezone } }, [preferences])
  const logout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' })
      queryClient.setQueryData(['me'], null)
      queryClient.clear()
      navigate('/login')
    } catch (error) { toast.error(error instanceof Error ? error.message : 'Falha ao sair') }
  }
  const links = [
    { to: '/', label: 'Visão geral', icon: LayoutDashboard },
    { to: '/library', label: 'Biblioteca', icon: BookOpen },
    { to: '/sessions', label: 'Sessões', icon: Activity },
    { to: '/goals', label: 'Metas', icon: GoalIcon },
    { to: '/statistics', label: 'Estatísticas', icon: BarChart3 },
  ]
  const mobileLinks = [...links, { to: '/integrations', label: 'Conexões', icon: Zap }, { to: '/settings', label: 'Perfil', icon: UserRound }]
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="/"><span className="brand-mark"><Gamepad2 size={20} /></span><span>game<span className="brand-accent">tracker</span></span></a>
      <div className="workspace-label">ESPAÇO PESSOAL</div>
      <nav className="side-nav">{links.map(({ to, label, icon: Icon }) => <a key={to} href={to} className={`nav-link ${location.pathname === to || (to !== '/' && location.pathname.startsWith(to)) ? 'active' : ''}`}><Icon size={18} /><span>{label}</span></a>)}</nav>
      <div className="sidebar-spacer" />
      <div className="sidebar-card"><div className="sidebar-card-icon"><Zap size={15} /></div><strong>Seu ritmo, do seu jeito</strong><span>Registre sessões para entender seus hábitos de jogo.</span><a href="/sessions">Registrar sessão <span>↗</span></a></div>
      <nav className="side-nav side-nav-bottom">
        <a href="/integrations" className={`nav-link ${location.pathname.startsWith('/integrations') ? 'active' : ''}`}><Zap size={18} /><span>Conexões</span></a>
        <a href="/settings" className={`nav-link ${location.pathname.startsWith('/settings') ? 'active' : ''}`}><Settings size={18} /><span>Configurações</span></a>
      </nav>
      <button className="user-chip" onClick={() => navigate('/settings')}><span className="avatar">{user.avatar_url ? <img src={user.avatar_url} alt="" /> : user.username.slice(0, 1).toUpperCase()}</span><span className="user-chip-text"><strong>{user.username}</strong><small>Conta pessoal</small></span><ChevronDown size={15} /></button>
    </aside>
    <main className="main-area"><header className="mobile-header"><a className="brand" href="/"><span className="brand-mark"><Gamepad2 size={18} /></span><span>game<span className="brand-accent">tracker</span></span></a><button aria-label="Sair" className="icon-button" onClick={logout}><LogOut size={18} /></button></header>
      <div className="mobile-nav">{mobileLinks.map(({ to, label, icon: Icon }) => <a key={to} href={to} aria-label={label} className={location.pathname === to || location.pathname.startsWith(`${to}/`) ? 'active' : ''}><Icon size={18} /><span>{label}</span></a>)}</div>
      <div className="content-area">{user.email === 'demo@gametracker.local' && <div className="demo-banner"><span>DEMO</span><p>Dados fictícios para demonstração. Nenhuma integração externa está conectada.</p></div>}<Outlet /></div>
      <footer className="app-footer"><span>GameTracker <span className="footer-dot">·</span> seus dados permanecem seus</span><button onClick={logout}><LogOut size={14} /> Sair da conta</button></footer>
    </main>
  </div>
}

function Protected({ user }: { user: User | null }) {
  if (!user) return <Navigate to="/login" replace />
  return <Shell user={user} />
}

export default function App() {
  const queryClient = useQueryClient()
  useEffect(() => { ensureCsrf().catch(() => undefined) }, [])
  const { data: user, isLoading } = useQuery({ queryKey: ['me'], queryFn: () => api<User>('/auth/me'), retry: false })
  const hasSession = Boolean(user)
  if (isLoading && location.pathname !== '/login') return <div className="full-loader"><LoadingState /></div>
  return <Routes>
    <Route path="/login" element={hasSession ? <Navigate to="/" replace /> : <AuthPage onLogin={(nextUser) => queryClient.setQueryData(['me'], nextUser)} />} />
    <Route element={<Protected user={user || null} />}>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/library" element={<LibraryPage />} />
      <Route path="/games/:id" element={<GamePage />} />
      <Route path="/sessions" element={<SessionsPage />} />
      <Route path="/goals" element={<GoalsPage />} />
      <Route path="/statistics" element={<StatisticsPage />} />
      <Route path="/integrations" element={<IntegrationsPage />} />
      <Route path="/settings" element={<SettingsPage user={user!} />} />
    </Route>
    <Route path="*" element={hasSession ? <NotFoundPage /> : <Navigate to="/login" replace />} />
  </Routes>
}
