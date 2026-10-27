import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, Clock3, Gamepad2, Goal, Plus, Timer, Trophy } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../lib/api'
import { formatDate } from '../lib/date'
import type { DashboardData } from '../types'
import { Button, Cover, EmptyState, ErrorState, LoadingState, PageTitle, Panel, Progress, StatCard } from '../components/Primitives'

const dayLabel = (date: string) => new Date(`${date}T12:00:00`).toLocaleDateString('pt-BR', { weekday: 'short' }).replace('.', '')

export default function DashboardPage() {
  const query = useQuery({ queryKey: ['dashboard'], queryFn: () => api<DashboardData>('/dashboard') })
  if (query.isLoading) return <LoadingState />
  if (query.isError) return <ErrorState message={query.error.message} retry={() => query.refetch()} />
  const data = query.data!
  const firstName = 'Olá, vamos jogar?'
  const hasActivity = data.totals.games > 0
  return <>
    <PageTitle eyebrow="CENTRAL DE ATIVIDADE" title={firstName} description="Um retrato do seu tempo e dos jogos que fazem parte dele." action={<Link to="/sessions"><Button><Plus size={16} /> Registrar sessão</Button></Link>} />
    {!hasActivity && <div className="welcome-banner"><div><span className="eyebrow">SEU ESPAÇO ESTÁ PRONTO</span><h2>Comece pela sua biblioteca.</h2><p>Adicione seus jogos e registre sessões. Seus indicadores aparecem aqui conforme você joga.</p></div><Link to="/library"><Button>Adicionar primeiro jogo <ArrowRight size={16} /></Button></Link><div className="welcome-art"><Gamepad2 size={86} /></div></div>}
    <div className="stats-grid">
      <StatCard label="Jogos na biblioteca" value={data.totals.games} detail="em todas as plataformas" icon={<Gamepad2 size={17} />} />
      <StatCard label="Tempo total" value={`${data.totals.hours}h`} detail="inclui dados importados" icon={<Clock3 size={17} />} />
      <StatCard label="Últimos 7 dias" value={`${data.totals.week_hours}h`} detail="tempo registrado" icon={<Activity size={17} />} />
      <StatCard label="Sessões" value={data.totals.sessions} detail="sessões concluídas" icon={<Timer size={17} />} />
    </div>
    <div className="dashboard-grid">
      <Panel title="Ritmo de jogo" action={<span className="panel-caption">ÚLTIMOS 7 DIAS</span>} className="activity-panel">
        {data.activity.every((day) => day.hours === 0) ? <EmptyState title="Sem sessões esta semana" detail="Registre seu tempo para acompanhar sua atividade diária." action={<Link to="/sessions"><Button variant="secondary">Registrar agora</Button></Link>} /> : <>
          <div className="chart-total"><strong>{data.totals.week_hours}<small>h</small></strong><span>nesta semana</span></div>
          <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.activity} margin={{ top: 10, right: 4, left: -24, bottom: 0 }}><defs><linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7185ff" stopOpacity={0.3} /><stop offset="95%" stopColor="#7185ff" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#242a35" vertical={false} /><XAxis dataKey="date" tickFormatter={dayLabel} axisLine={false} tickLine={false} tick={{ fill: '#737d8d', fontSize: 11 }} dy={8} /><YAxis axisLine={false} tickLine={false} tick={{ fill: '#737d8d', fontSize: 10 }} /><Tooltip contentStyle={{ background: '#171b24', border: '1px solid #2b3140', borderRadius: 10, color: '#eef0f6' }} labelFormatter={(value) => new Date(`${value}T12:00:00`).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' })} formatter={(value) => [`${value} h`, 'Tempo jogado']} /><Area type="monotone" dataKey="hours" stroke="#8291ff" strokeWidth={2.5} fill="url(#activityFill)" activeDot={{ r: 4, fill: '#9ba7ff', stroke: '#171b24', strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div>
        </>}
      </Panel>
      <Panel title="Meta semanal" action={<Link className="text-link" to="/settings">Editar meta <ArrowRight size={13} /></Link>} className="goal-panel">
        <div className="goal-ring" style={{ '--progress': `${data.weekly_goal.percentage}%` } as CSSProperties}><div><strong>{data.weekly_goal.percentage}%</strong><span>concluído</span></div></div>
        <div className="goal-summary"><span>{data.weekly_goal.progress}h de {data.weekly_goal.target}h</span><Progress value={data.weekly_goal.percentage} /><small>{data.weekly_goal.percentage >= 100 ? 'Meta da semana alcançada. Boa!' : `Faltam ${Math.max(0, data.weekly_goal.target - data.weekly_goal.progress).toFixed(1)}h para sua meta.`}</small></div>
        <div className="goal-mini-stats"><span><Trophy size={15} /> {data.totals.most_played?.name || 'Nenhum jogo registrado'}</span><span>Mais jogado</span></div>
      </Panel>
    </div>
    <div className="dashboard-grid lower-grid">
      <Panel title="Jogos recentes" action={<Link className="text-link" to="/library">Ver biblioteca <ArrowRight size={13} /></Link>}>
        {data.recent_games.length === 0 ? <EmptyState title="Sua coleção começa aqui" detail="Adicione jogos manualmente ou conecte uma plataforma compatível." action={<Link to="/library"><Button variant="secondary">Explorar biblioteca</Button></Link>} /> : <div className="recent-game-list">{data.recent_games.slice(0, 5).map((game) => <Link to={`/games/${game.id}`} key={game.id} className="recent-game-row"><Cover src={game.cover_url} name={game.name} /><span className="recent-game-info"><strong>{game.name}</strong><small>{game.platform} <span>·</span> {game.status === 'playing' ? 'Jogando' : game.status === 'completed' ? 'Concluído' : game.status === 'paused' ? 'Pausado' : 'Quero jogar'}</small></span><span className="recent-game-hours">{game.total_played_hours}h</span><ArrowRight size={14} className="row-arrow" /></Link>)}</div>}
      </Panel>
      <Panel title="Sessões recentes" action={<Link className="text-link" to="/sessions">Histórico <ArrowRight size={13} /></Link>}>
        {data.recent_sessions.length === 0 ? <EmptyState title="Seu histórico aparece aqui" detail="Registre sessões manualmente ou use o contador enquanto joga." /> : <div className="session-list">{data.recent_sessions.map((session) => <div key={session.id} className="session-row"><span className="session-dot" /><span className="session-info"><strong>{session.game_name}</strong><small>{formatDate(session.started_at, { day: 'numeric', month: 'short' })}</small></span><span>{(session.duration_seconds / 3600).toFixed(1)}h</span></div>)}</div>}
      </Panel>
    </div>
    {data.goals.length > 0 && <Panel title="Metas em andamento" action={<Link className="text-link" to="/goals">Ver todas <ArrowRight size={13} /></Link>} className="goals-strip">{data.goals.map((goal) => <div key={goal.id} className="goal-strip-item"><div className="goal-strip-head"><strong>{goal.title}</strong><span>{goal.percentage}%</span></div><Progress value={goal.percentage} /><small>{goal.progress} / {goal.target} {goal.goal_type.includes('hours') ? 'h' : 'dias'}</small></div>)}</Panel>}
    <div className="month-note"><span><Activity size={15} /></span><div><strong>Resumo do mês</strong><small>Você registrou {data.monthly_hours} horas neste mês. {data.totals.most_played ? `Seu jogo mais jogado é ${data.totals.most_played.name}.` : 'Comece a registrar sessões para ver seu resumo.'}</small></div></div>
  </>
}
