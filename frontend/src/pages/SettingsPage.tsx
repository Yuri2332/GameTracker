import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Download, Moon, Pencil, ShieldCheck, Sun, Trash2, UserRound, Clock3 } from 'lucide-react'
import { toast } from 'sonner'
import { api, downloadExport } from '../lib/api'
import { formatDate } from '../lib/date'
import type { User } from '../types'
import { Button, ErrorState, FormField, LoadingState, PageTitle, Panel } from '../components/Primitives'

type Preferences = { theme: 'dark' | 'light'; weekly_goal_hours: number; timezone: string; profile_public: boolean }
type Profile = { username: string; email: string; avatar_url: string | null; created_at: string; totals: { games: number; hours: number; sessions: number; most_played: { name: string } | null } }

export default function SettingsPage({ user }: { user: User }) {
  const query = useQuery({ queryKey: ['settings'], queryFn: () => api<Preferences>('/settings') })
  const profile = useQuery({ queryKey: ['profile'], queryFn: () => api<Profile>('/profile') })
  const [prefs, setPrefs] = useState<Preferences | null>(null)
  const [editingProfile, setEditingProfile] = useState(false)
  const [saving, setSaving] = useState(false)
  const client = useQueryClient()
  const navigate = useNavigate()
  useEffect(() => { if (query.data) setPrefs(query.data) }, [query.data])
  useEffect(() => { if (prefs) { document.documentElement.dataset.theme = prefs.theme; document.documentElement.dataset.timezone = prefs.timezone } }, [prefs?.theme, prefs?.timezone])
  const save = useMutation({ mutationFn: () => api<Preferences>('/settings', { method: 'PATCH', body: JSON.stringify(prefs) }), onSuccess: (data) => { setPrefs(data); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Preferências salvas.') }, onError: (e) => toast.error(e.message) })
  const saveProfile = useMutation({ mutationFn: (form: FormData) => api<User>('/profile', { method: 'PATCH', body: JSON.stringify({ username: form.get('username'), avatar_url: form.get('avatar_url') || null }) }), onSuccess: (data) => { client.setQueryData(['me'], data); client.invalidateQueries({ queryKey: ['profile'] }); setEditingProfile(false); toast.success('Perfil atualizado.') }, onError: (e) => toast.error(e.message) })
  const removeAccount = useMutation({ mutationFn: () => api('/profile', { method: 'DELETE' }), onSuccess: () => { client.clear(); navigate('/login'); toast.success('Conta e dados pessoais excluídos.') }, onError: (e) => toast.error(e.message) })
  if (query.isLoading || profile.isLoading) return <LoadingState />
  if (query.isError || profile.isError) return <ErrorState message={(query.error || profile.error)?.message} retry={() => { query.refetch(); profile.refetch() }} />
  if (!prefs) return <LoadingState />
  const profileData = profile.data!
  return <>
    <PageTitle eyebrow="SUA CONTA" title="Perfil e configurações" description="Gerencie suas preferências e os dados armazenados na sua conta." />
    <Panel title="Perfil" action={<Button variant="ghost" onClick={() => setEditingProfile(true)}><Pencil size={14} /> Editar perfil</Button>}><div className="profile-overview"><span className="profile-avatar">{user.avatar_url ? <img src={user.avatar_url} alt="Avatar" /> : user.username.slice(0, 1).toUpperCase()}</span><div className="profile-main"><h2>{user.username}</h2><span>{user.email}</span><small>Membro desde {formatDate(profileData.created_at, { month: 'long', year: 'numeric' })}</small></div><div className="profile-stats"><span><strong>{profileData.totals.games}</strong> jogos</span><span><strong>{profileData.totals.hours}</strong> horas</span><span><strong>{profileData.totals.sessions}</strong> sessões</span></div></div><div className="favorite-profile"><UserRound size={15} /><span>Jogo mais jogado</span><strong>{profileData.totals.most_played?.name || 'Ainda não há sessões registradas'}</strong></div></Panel>
    <Panel title="Preferências"><div className="settings-form">
      <div className="setting-row"><div className="setting-copy"><strong>Tema</strong><span>Escolha como o GameTracker aparece neste dispositivo.</span></div><div className="theme-picker"><button className={prefs.theme === 'dark' ? 'selected' : ''} onClick={() => setPrefs({ ...prefs, theme: 'dark' })}><Moon size={15} /> Escuro</button><button className={prefs.theme === 'light' ? 'selected' : ''} onClick={() => setPrefs({ ...prefs, theme: 'light' })}><Sun size={15} /> Claro</button></div></div>
      <div className="setting-row"><div className="setting-copy"><strong>Meta semanal padrão</strong><span>Usada no resumo do dashboard.</span></div><label className="inline-number"><input aria-label="Meta semanal em horas" type="number" min="1" max="168" step="1" value={prefs.weekly_goal_hours} onChange={(e) => setPrefs({ ...prefs, weekly_goal_hours: Number(e.target.value) })} /><span>horas</span></label></div>
      <div className="setting-row"><div className="setting-copy"><strong>Fuso horário</strong><span>Aplicado à exibição de datas e horários.</span></div><FormField label="Fuso horário"><select value={prefs.timezone} onChange={(e) => setPrefs({ ...prefs, timezone: e.target.value })}><option value="America/Sao_Paulo">Brasília (UTC−03:00)</option><option value="America/Manaus">Manaus (UTC−04:00)</option><option value="America/Belem">Belém (UTC−03:00)</option><option value="UTC">UTC</option></select></FormField></div>
      <div className="setting-row"><div className="setting-copy"><strong>Perfil público</strong><span>Preferência registrada para um perfil público futuro.</span></div><label className="switch"><input type="checkbox" checked={prefs.profile_public} onChange={(e) => setPrefs({ ...prefs, profile_public: e.target.checked })} /><span /></label></div>
      <div className="settings-save"><Button disabled={save.isPending} onClick={() => save.mutate()}>{save.isPending ? 'Salvando…' : 'Salvar preferências'}</Button></div>
    </div></Panel>
    <Panel title="Privacidade e dados"><div className="privacy-cards"><div className="privacy-card"><div className="privacy-icon"><ShieldCheck size={17} /></div><div><strong>Conta privada por padrão</strong><p>Sua biblioteca, sessões e estatísticas só ficam disponíveis após autenticar na sua conta.</p></div></div><div className="privacy-card"><div className="privacy-icon"><Download size={17} /></div><div><strong>Exportar seus dados</strong><p>Baixe sua biblioteca e o histórico de sessões em um formato portátil.</p><div className="export-actions"><Button variant="secondary" onClick={() => downloadExport('json')}><Download size={14} /> JSON</Button><Button variant="secondary" onClick={() => downloadExport('csv')}><Download size={14} /> CSV de sessões</Button></div></div></div><div className="privacy-card"><div className="privacy-icon"><Clock3 size={17} /></div><div><strong>Recuperação de senha</strong><p>O envio de e-mail ainda não foi configurado neste ambiente. Use uma senha forte e mantenha acesso ao e-mail da conta.</p></div></div></div></Panel>
    <Panel title="Excluir conta" className="danger-panel"><div className="danger-zone"><div><strong>Apagar conta e dados</strong><p>Isso exclui permanentemente sua biblioteca, sessões, metas e conexões. Os dados não poderão ser recuperados.</p></div><Button variant="danger" disabled={removeAccount.isPending} onClick={() => { if (window.prompt('Para confirmar, digite APAGAR') === 'APAGAR') removeAccount.mutate() }}><Trash2 size={15} /> Excluir conta</Button></div></Panel>
    {editingProfile && <div className="modal-backdrop"><section className="modal-card" role="dialog" aria-modal="true"><div className="modal-heading"><div><span className="eyebrow">SUA IDENTIDADE</span><h2>Editar perfil</h2></div><button className="icon-button" onClick={() => setEditingProfile(false)} aria-label="Fechar">×</button></div><form className="form-grid" onSubmit={(event) => { event.preventDefault(); saveProfile.mutate(new FormData(event.currentTarget)) }}><FormField label="Nome de usuário"><input name="username" required minLength={3} maxLength={40} pattern="[A-Za-z0-9_-]+" defaultValue={user.username} /></FormField><FormField label="Avatar por URL (opcional)"><input name="avatar_url" type="url" maxLength={500} defaultValue={user.avatar_url || ''} placeholder="https://…" /></FormField><div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setEditingProfile(false)}>Cancelar</Button><Button type="submit" disabled={saveProfile.isPending}>{saveProfile.isPending ? 'Salvando…' : 'Salvar perfil'}</Button></div></form></section></div>}
  </>
}
