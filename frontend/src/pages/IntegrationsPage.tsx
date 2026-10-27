import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Check, CircleAlert, ExternalLink, RefreshCw, Shield, Unplug, Zap } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import { formatDateTime } from '../lib/date'
import { Button, ErrorState, LoadingState, PageTitle, Panel } from '../components/Primitives'

type Integration = { provider: string; name: string; configured: boolean; connected: boolean; account_id?: string | null; last_synced_at?: string | null; note: string; logs?: { id: string; started_at: string; status: string; message: string | null; imported_count: number; total_count: number }[] }

export default function IntegrationsPage() {
  const [params, setParams] = useSearchParams()
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['integrations'], queryFn: () => api<{ items: Integration[] }>('/integrations') })
  useEffect(() => { const state = params.get('steam'); const reason = params.get('reason'); if (state === 'connected') toast.success('Conta Steam conectada.'); if (state === 'error') toast.error(reason || 'Não foi possível conectar a Steam.'); if (state) setParams({}, { replace: true }) }, [params, setParams])
  const sync = useMutation({ mutationFn: () => api<{ imported: number; total: number; cached: boolean }>('/integrations/steam/sync', { method: 'POST' }), onSuccess: (data) => { client.invalidateQueries({ queryKey: ['integrations'] }); client.invalidateQueries({ queryKey: ['games'] }); client.invalidateQueries({ queryKey: ['dashboard'] }); toast.success(data.cached ? 'A biblioteca Steam já foi sincronizada há menos de um minuto.' : `${data.imported} jogos novos importados; ${data.total} verificados.`) }, onError: (e) => { client.invalidateQueries({ queryKey: ['integrations'] }); toast.error(e.message) } })
  const disconnect = useMutation({ mutationFn: () => api('/integrations/steam', { method: 'DELETE' }), onSuccess: () => { client.invalidateQueries({ queryKey: ['integrations'] }); toast.success('Steam desconectada. Os jogos já importados continuam na biblioteca.') }, onError: (e) => toast.error(e.message) })
  if (query.isLoading) return <LoadingState />
  if (query.isError) return <ErrorState message={query.error.message} retry={() => query.refetch()} />
  const steam = query.data!.items[0]
  return <>
    <PageTitle eyebrow="CONTAS CONECTADAS" title="Conexões" description="Importe dados de plataformas compatíveis. Você controla quando sincronizar e pode desconectar a qualquer momento." />
    <div className="integration-callout"><Shield size={17} /><span>Conexões usam somente os dados autorizados pela plataforma. Credenciais e chaves ficam no backend.</span></div>
    <Panel title="Disponíveis agora" action={<span className="panel-caption">{steam.configured ? 'STEAM CONFIGURADA' : 'INTEGRAÇÃO OPCIONAL'}</span>}>
      <article className="integration-card"><div className="integration-logo steam-logo">S</div><div className="integration-main"><div className="integration-title"><h3>Steam</h3>{steam.connected ? <span className="connection-state connected"><i /> Conectada</span> : <span className="connection-state"><i /> Desconectada</span>}</div><p>{steam.note}</p>{steam.connected && <div className="integration-meta"><span>ID Steam: {steam.account_id}</span><span>Última sincronização: {steam.last_synced_at ? formatDateTime(steam.last_synced_at) : 'Ainda não sincronizada'}</span></div>}{!steam.configured && <div className="integration-warning"><CircleAlert size={15} /> O administrador precisa definir <code>STEAM_API_KEY</code> e <code>STEAM_REDIRECT_URL</code> no servidor.</div>}</div><div className="integration-actions">{steam.connected ? <><Button variant="secondary" disabled={sync.isPending} onClick={() => sync.mutate()}><RefreshCw size={15} className={sync.isPending ? 'spin' : ''} /> {sync.isPending ? 'Sincronizando…' : 'Sincronizar'}</Button><Button variant="ghost" disabled={disconnect.isPending} onClick={() => window.confirm('Desconectar a Steam? Jogos importados permanecerão na biblioteca.') && disconnect.mutate()}><Unplug size={15} /> Desconectar</Button></> : <Button disabled={!steam.configured} onClick={() => { window.location.href = '/api/integrations/steam/connect' }}>Conectar Steam <ExternalLink size={14} /></Button>}</div></article>
    </Panel>
    {steam.logs?.length ? <Panel title="Histórico de sincronização"><div className="sync-log-list">{steam.logs.map((log) => <div className="sync-log-row" key={log.id}><span className={`sync-log-icon ${log.status}`}>{log.status === 'success' ? <Check size={14} /> : <CircleAlert size={14} />}</span><div><strong>{log.status === 'success' ? 'Sincronização concluída' : 'Falha na sincronização'}</strong><small>{formatDateTime(log.started_at)} {log.message && `· ${log.message}`}</small></div>{log.status === 'success' && <span>{log.imported_count} novos</span>}</div>)}</div></Panel> : null}
    <Panel title="Planejadas para o futuro"><div className="integration-future-grid">{query.data!.items.slice(1).map((integration) => <article className="future-integration" key={integration.provider}><div className="future-icon"><Zap size={17} /></div><div><h3>{integration.name}</h3><p>{integration.note}</p><span>Indisponível por enquanto</span></div></article>)}</div></Panel>
    <div className="integration-footnote">A Steam só retorna bibliotecas com visibilidade compatível e pode impor limites temporários de requisição. O GameTracker não detecta jogos abertos automaticamente.</div>
  </>
}
