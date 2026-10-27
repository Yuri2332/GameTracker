import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownWideNarrow, Grid2X2, Heart, List, Plus, Search, SlidersHorizontal, Star, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import type { Game } from '../types'
import { Button, Cover, EmptyState, ErrorState, FormField, LoadingState, PageTitle } from '../components/Primitives'

type GameList = { items: Game[]; total: number }
const statusLabels: Record<string, string> = { backlog: 'Quero jogar', playing: 'Jogando', paused: 'Pausado', completed: 'Concluído' }

export default function LibraryPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [platform, setPlatform] = useState('')
  const [genre, setGenre] = useState('')
  const [sort, setSort] = useState('recent')
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [showForm, setShowForm] = useState(false)
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [page, setPage] = useState(1)
  const client = useQueryClient()
  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (status) params.set('status', status)
  if (platform) params.set('platform', platform)
  if (genre) params.set('genre', genre)
  if (favoriteOnly) params.set('favorite', 'true')
  params.set('sort', sort)
  params.set('page', String(page))
  const query = useQuery({ queryKey: ['games', search, status, platform, genre, favoriteOnly, sort, page], queryFn: () => api<GameList>(`/games?${params}`) })
  const remove = useMutation({ mutationFn: (id: string) => api(`/games/${id}`, { method: 'DELETE' }), onSuccess: () => { client.invalidateQueries({ queryKey: ['games'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Jogo removido da biblioteca.') }, onError: (e) => toast.error(e.message) })
  const platforms = useMemo(() => Array.from(new Set(query.data?.items.map((game) => game.platform) || [])), [query.data])
  const genres = useMemo(() => Array.from(new Set(query.data?.items.map((game) => game.genre).filter((value): value is string => Boolean(value)) || [])), [query.data])
  const create = useMutation({ mutationFn: (form: FormData) => api<Game>('/games', { method: 'POST', body: JSON.stringify({ name: form.get('name'), platform: form.get('platform'), genre: form.get('genre') || null, cover_url: form.get('cover_url') || null, status: form.get('status'), favorite: form.get('favorite') === 'on', tags: String(form.get('tags') || '').split(',').map((tag) => tag.trim()).filter(Boolean) }) }), onSuccess: () => { setShowForm(false); client.invalidateQueries({ queryKey: ['games'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success('Jogo adicionado à sua biblioteca.') }, onError: (e) => toast.error(e.message) })
  return <>
    <PageTitle eyebrow="SUA COLEÇÃO" title="Biblioteca" description={`${query.data?.total ?? '—'} jogos guardados no seu espaço.`} action={<Button onClick={() => setShowForm(true)}><Plus size={16} /> Adicionar jogo</Button>} />
    <div className="library-toolbar"><div className="search-box"><Search size={16} /><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} placeholder="Buscar na biblioteca…" aria-label="Buscar jogo" /></div>
      <div className="toolbar-filters"><SlidersHorizontal size={15} /><select aria-label="Filtrar por status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}><option value="">Todos os status</option>{Object.entries(statusLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select>
        <select aria-label="Filtrar por plataforma" value={platform} onChange={(e) => { setPlatform(e.target.value); setPage(1) }}><option value="">Todas plataformas</option>{platforms.map((item) => <option key={item}>{item}</option>)}</select>
        <select aria-label="Filtrar por gênero" value={genre} onChange={(e) => { setGenre(e.target.value); setPage(1) }}><option value="">Todos os gêneros</option>{genres.map((item) => <option key={item}>{item}</option>)}</select>
        <select aria-label="Ordenar biblioteca" value={sort} onChange={(e) => { setSort(e.target.value); setPage(1) }}><option value="recent">Mais recentes</option><option value="name">Nome</option><option value="hours">Mais jogados</option><option value="rating">Melhor avaliação</option></select>
        <button className={`filter-chip ${favoriteOnly ? 'selected' : ''}`} onClick={() => { setFavoriteOnly(!favoriteOnly); setPage(1) }} aria-pressed={favoriteOnly}><Heart size={14} /> Favoritos</button>
        <div className="view-toggle"><button aria-label="Grade" className={view === 'grid' ? 'selected' : ''} onClick={() => setView('grid')}><Grid2X2 size={16} /></button><button aria-label="Lista" className={view === 'list' ? 'selected' : ''} onClick={() => setView('list')}><List size={16} /></button></div>
      </div>
    </div>
    {query.isLoading ? <LoadingState /> : query.isError ? <ErrorState message={query.error.message} retry={() => query.refetch()} /> : query.data!.items.length === 0 ? <EmptyState title={search || status || favoriteOnly ? 'Nenhum jogo encontrado' : 'Sua biblioteca está vazia'} detail={search || status || favoriteOnly ? 'Ajuste os filtros ou cadastre este jogo manualmente.' : 'Cadastre seus jogos para organizar sua coleção e começar a registrar sessões.'} action={<Button onClick={() => setShowForm(true)}><Plus size={15} /> Cadastrar manualmente</Button>} /> : view === 'grid' ? <div className="game-grid">{query.data!.items.map((game) => <article className="game-card" key={game.id}><Link className="game-card-main" to={`/games/${game.id}`}><Cover src={game.cover_url} name={game.name} /><div className="game-card-meta"><div className="game-card-title"><strong>{game.name}</strong>{game.favorite && <Heart size={13} fill="currentColor" />}</div><span>{game.platform} <i>·</i> {game.genre || 'Sem gênero'}</span><div className="game-card-bottom"><span className={`status-pill status-${game.status}`}>{statusLabels[game.status]}</span><small>{game.total_played_hours}h</small></div></div></Link><button aria-label={`Remover ${game.name}`} className="game-delete" onClick={() => window.confirm(`Remover ${game.name} e suas sessões?`) && remove.mutate(game.id)}><Trash2 size={14} /></button></article>)}</div> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Jogo</th><th>Plataforma</th><th>Status</th><th>Tempo</th><th>Nota</th><th></th></tr></thead><tbody>{query.data!.items.map((game) => <tr key={game.id}><td><Link to={`/games/${game.id}`} className="table-game"><Cover src={game.cover_url} name={game.name} /><strong>{game.name}</strong></Link></td><td>{game.platform}</td><td><span className={`status-pill status-${game.status}`}>{statusLabels[game.status]}</span></td><td>{game.total_played_hours}h</td><td>{game.rating == null ? '—' : <span className="rating-value"><Star size={13} fill="currentColor" /> {game.rating.toFixed(1)}</span>}</td><td><button aria-label="Remover jogo" className="icon-button subtle" onClick={() => window.confirm(`Remover ${game.name} e suas sessões?`) && remove.mutate(game.id)}><Trash2 size={15} /></button></td></tr>)}</tbody></table></div>}
    {query.data && query.data.total > 50 && <div className="pagination"><span>{(page - 1) * 50 + 1}–{Math.min(page * 50, query.data.total)} de {query.data.total}</span><div><Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Anterior</Button><Button variant="secondary" disabled={page * 50 >= query.data.total} onClick={() => setPage(page + 1)}>Próxima</Button></div></div>}
    {showForm && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setShowForm(false)}><section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="add-game-title"><div className="modal-heading"><div><span className="eyebrow">NOVO REGISTRO</span><h2 id="add-game-title">Adicionar jogo</h2></div><button className="icon-button" onClick={() => setShowForm(false)} aria-label="Fechar">×</button></div><p>Cadastre as informações disponíveis. Você pode completar os detalhes depois.</p><form className="form-grid" onSubmit={(event) => { event.preventDefault(); create.mutate(new FormData(event.currentTarget)) }}>
      <FormField label="Nome do jogo"><input name="name" required maxLength={160} placeholder="Ex.: Hades II" /></FormField><FormField label="Plataforma"><select name="platform" defaultValue="PC"><option>PC</option><option>Steam</option><option>PlayStation 5</option><option>PlayStation 4</option><option>Xbox Series X|S</option><option>Xbox One</option><option>Nintendo Switch</option><option>Outra</option></select></FormField>
      <FormField label="Gênero"><input name="genre" maxLength={80} placeholder="Ex.: RPG de ação" /></FormField><FormField label="Status"><select name="status" defaultValue="backlog"><option value="backlog">Quero jogar</option><option value="playing">Jogando</option><option value="paused">Pausado</option><option value="completed">Concluído</option></select></FormField>
      <FormField label="URL da capa (opcional)"><input name="cover_url" type="url" placeholder="https://…" /></FormField><FormField label="Tags, separadas por vírgula"><input name="tags" placeholder="co-op, história, indie" /></FormField><label className="checkbox-field"><input name="favorite" type="checkbox" /> Marcar como favorito</label>
      <div className="modal-actions"><Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancelar</Button><Button type="submit" disabled={create.isPending}>{create.isPending ? 'Salvando…' : 'Adicionar jogo'}</Button></div>
    </form></section></div>}
  </>
}
