import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, Check, CirclePause, Goal as GoalIcon, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import type { Game, Goal } from '../types'
import { Button, EmptyState, ErrorState, FormField, LoadingState, PageTitle, Panel, Progress } from '../components/Primitives'

type List<T> = { items: T[] }
const labels: Record<string, string> = { weekly_hours: 'Jogar horas nesta semana', game_hours: 'Jogar horas em um jogo', active_days: 'Jogar em dias diferentes', finish_game: 'Concluir um jogo' }
const unit: Record<string, string> = { weekly_hours: 'h', game_hours: 'h', active_days: 'dias', finish_game: 'jogo(s)' }
const dateInput = (value?: string | null) => value || ''

export default function GoalsPage() {
  const client = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Goal | null>(null)
  const [type, setType] = useState('weekly_hours')
  const [error, setError] = useState('')
  const goals = useQuery({ queryKey: ['goals'], queryFn: () => api<List<Goal>>('/goals') })
  const games = useQuery({ queryKey: ['games'], queryFn: () => api<List<Game>>('/games?limit=100') })
  const save = useMutation({ mutationFn: ({ form, goal }: { form: FormData; goal: Goal | null }) => {
    const payload = { title: form.get('title'), description: form.get('description') || null, goal_type: form.get('goal_type'), target: Number(form.get('target')), deadline: form.get('deadline') || null, game_ids: form.getAll('game_ids') }
    return api(goal ? `/goals/${goal.id}` : '/goals', { method: goal ? 'PATCH' : 'POST', body: JSON.stringify(payload) })
  }, onSuccess: () => { setShowForm(false); setEditing(null); client.invalidateQueries({ queryKey: ['goals'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Meta salva.') }, onError: (e) => setError(e.message) })
  const update = useMutation({ mutationFn: ({ id, status }: { id: string; status: string }) => api(`/goals/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }), onSuccess: () => { client.invalidateQueries({ queryKey: ['goals'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Status da meta atualizado.') }, onError: (e) => toast.error(e.message) })
  const remove = useMutation({ mutationFn: (id: string) => api(`/goals/${id}`, { method: 'DELETE' }), onSuccess: () => { client.invalidateQueries({ queryKey: ['goals'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Meta removida.') }, onError: (e) => toast.error(e.message) })
  if (goals.isLoading || games.isLoading) return <LoadingState />
  if (goals.isError || games.isError) return <ErrorState message={(goals.error || games.error)?.message} retry={() => { goals.refetch(); games.refetch() }} />
  const all = goals.data!.items
  const active = all.filter((goal) => goal.status === 'active')
  const past = all.filter((goal) => goal.status !== 'active')
  const launchForm = (goal: Goal | null = null) => { setEditing(goal); setType(goal?.goal_type || 'weekly_hours'); setError(''); setShowForm(true) }
  return <>
    <PageTitle eyebrow="PROGRESSO PESSOAL" title="Metas" description="Transforme seus planos de jogo em marcos que acompanham seu ritmo." action={<Button onClick={() => launchForm()}><Plus size={16} /> Criar meta</Button>} />
    <div className="goal-intro"><div className="goal-intro-icon"><GoalIcon size={19} /></div><div><strong>O progresso vem das suas sessões e da sua biblioteca.</strong><span>Metas de horas e dias se atualizam automaticamente com o que você registra.</span></div></div>
    <Panel title="Em andamento" action={<span className="panel-caption">{active.length} ATIVAS</span>}>
      {active.length === 0 ? <EmptyState title="Nenhuma meta ativa" detail="Crie uma meta semanal, um objetivo de tempo ou um desafio para concluir um jogo." action={<Button onClick={() => launchForm()}><Plus size={15} /> Criar minha primeira meta</Button>} /> : <div className="goals-grid">{active.map((goal) => <article className="goal-card goal-full-card" key={goal.id}><div className="goal-card-top"><span className="goal-type-icon"><GoalIcon size={16} /></span><div className="goal-card-actions"><button className="icon-button subtle" aria-label="Editar meta" onClick={() => launchForm(goal)}><PencilIcon /></button><button className="icon-button subtle" aria-label="Pausar meta" onClick={() => update.mutate({ id: goal.id, status: 'paused' })}><CirclePause size={15} /></button><button className="icon-button subtle" aria-label="Excluir meta" onClick={() => window.confirm(`Excluir a meta “${goal.title}”?`) && remove.mutate(goal.id)}><Trash2 size={15} /></button></div></div><h3>{goal.title}</h3><p>{goal.description || labels[goal.goal_type]}</p><div className="goal-progress-line"><strong>{goal.progress}<small> {unit[goal.goal_type]}</small></strong><span>{goal.percentage}%</span></div><Progress value={goal.percentage} /><div className="goal-card-footer"><span>{goal.progress >= goal.target ? <><Check size={13} /> Objetivo concluído</> : `${Math.max(0, goal.target - goal.progress).toFixed(1)} ${unit[goal.goal_type]} restantes`}</span>{goal.deadline && <span><CalendarDays size={13} /> Até {new Date(`${goal.deadline}T00:00:00`).toLocaleDateString('pt-BR')}</span>}</div></article>)}</div>}
    </Panel>
    {past.length > 0 && <Panel title="Pausadas e concluídas" className="past-goals-panel"><div className="past-goal-list">{past.map((goal) => <div className="past-goal-row" key={goal.id}><span className={`past-goal-mark ${goal.status}`}>{goal.status === 'completed' ? <Check size={14} /> : <CirclePause size={14} />}</span><div><strong>{goal.title}</strong><small>{goal.status === 'completed' ? 'Concluída' : 'Pausada'} · {goal.progress} / {goal.target} {unit[goal.goal_type]}</small></div><div className="past-goal-actions">{goal.status === 'paused' && <button className="icon-button subtle" aria-label="Retomar meta" onClick={() => update.mutate({ id: goal.id, status: 'active' })}><RotateCcw size={15} /></button>}<button className="icon-button subtle" aria-label="Excluir meta" onClick={() => window.confirm(`Excluir a meta “${goal.title}”?`) && remove.mutate(goal.id)}><Trash2 size={15} /></button></div></div>)}</div></Panel>}
    {showForm && <div className="modal-backdrop"><section className="modal-card" role="dialog" aria-modal="true"><div className="modal-heading"><div><span className="eyebrow">{editing ? 'ATUALIZAR OBJETIVO' : 'NOVO OBJETIVO'}</span><h2>{editing ? 'Editar meta' : 'Criar meta'}</h2></div><button className="icon-button" onClick={() => setShowForm(false)} aria-label="Fechar">×</button></div><form className="form-grid" onSubmit={(e) => { e.preventDefault(); setError(''); save.mutate({ form: new FormData(e.currentTarget), goal: editing }) }}>
      <FormField label="Título"><input name="title" required maxLength={120} defaultValue={editing?.title || ''} placeholder="Ex.: Jogar um pouco todo dia" /></FormField><FormField label="Tipo de meta"><select name="goal_type" value={type} onChange={(e) => setType(e.target.value)}><option value="weekly_hours">Horas durante a semana</option><option value="game_hours">Horas em um jogo</option><option value="active_days">Dias diferentes na semana</option><option value="finish_game">Concluir jogo(s)</option></select></FormField>
      <FormField label="Objetivo"><input name="target" type="number" min="0.5" max="10000" step="0.5" required defaultValue={editing?.target || (type === 'weekly_hours' ? 10 : type === 'active_days' ? 3 : 20)} /></FormField><FormField label="Prazo (opcional)"><input name="deadline" type="date" defaultValue={dateInput(editing?.deadline)} /></FormField>
      <FormField label="Descrição (opcional)"><input name="description" maxLength={2000} defaultValue={editing?.description || ''} placeholder="Um objetivo pessoal…" /></FormField>
      {(type === 'game_hours' || type === 'finish_game') && <fieldset className="game-picker"><legend>Jogos relacionados</legend>{games.data!.items.length === 0 ? <p>Adicione jogos à biblioteca antes de criar esta meta.</p> : games.data!.items.map((game) => <label key={game.id}><input type="checkbox" name="game_ids" value={game.id} defaultChecked={editing?.game_ids.includes(game.id)} /> {game.name}</label>)}</fieldset>}
      {error && <div role="alert" className="form-error">{error}</div>}<div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancelar</Button><Button type="submit" disabled={save.isPending}>{save.isPending ? 'Salvando…' : editing ? 'Salvar alterações' : 'Criar meta'}</Button></div>
    </form></section></div>}
  </>
}

function PencilIcon() { return <span style={{ fontSize: 14 }}>✎</span> }
