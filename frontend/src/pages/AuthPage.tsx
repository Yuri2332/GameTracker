import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Activity, ArrowRight, Gamepad2, ShieldCheck, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../lib/api'
import type { User } from '../types'
import { Button, FormField } from '../components/Primitives'

export default function AuthPage({ onLogin }: { onLogin: (user: User) => void }) {
  const [registering, setRegistering] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: (form: FormData) => api<User>(registering ? '/auth/register' : '/auth/login', {
      method: 'POST', body: JSON.stringify(registering ? { email: form.get('email'), username: form.get('username'), password: form.get('password') } : { email: form.get('email'), password: form.get('password') }),
    }),
    onSuccess: (user) => { onLogin(user); navigate('/'); toast.success(registering ? 'Sua conta está pronta.' : 'Boas-vindas de volta.') },
    onError: (err) => setError(err instanceof Error ? err.message : 'Não foi possível entrar.'),
  })
  return <div className="auth-screen">
    <section className="auth-visual"><div className="auth-visual-inner"><a className="brand brand-large" href="/"><span className="brand-mark"><Gamepad2 size={22} /></span><span>game<span className="brand-accent">tracker</span></span></a>
      <div className="auth-copy"><div className="eyebrow"><span className="live-dot" /> SUA JORNADA, EM UM SÓ LUGAR</div><h1>Todo jogo tem<br /><span>uma história.</span></h1><p>Guarde seus momentos, acompanhe seus hábitos e escolha o próximo capítulo.</p>
        <div className="auth-feature"><span><Activity size={17} /></span><div><strong>Atividade que faz sentido</strong><small>Veja como seu tempo se distribui ao longo dos dias.</small></div></div>
        <div className="auth-feature"><span><ShieldCheck size={17} /></span><div><strong>Seus dados, sob seu controle</strong><small>Uma biblioteca privada, sem conexão obrigatória.</small></div></div>
      </div><div className="auth-visual-foot"><span><Sparkles size={14} /> Feito para quem joga com intenção</span><span>01 / 04</span></div>
    </div></section>
    <section className="auth-form-wrap"><div className="auth-form"><div className="auth-mobile-brand"><span className="brand-mark"><Gamepad2 size={18} /></span> gametracker</div><div className="eyebrow">{registering ? 'COMECE POR AQUI' : 'SEU ESPAÇO DE JOGO'}</div><h2>{registering ? 'Crie sua conta' : 'Que bom ter você de volta'}</h2><p className="auth-subtitle">{registering ? 'Sua biblioteca começa com o primeiro jogo.' : 'Entre para continuar acompanhando sua jornada.'}</p>
      <form onSubmit={(event) => { event.preventDefault(); setError(''); mutation.mutate(new FormData(event.currentTarget)) }}>
        {registering && <FormField label="Nome de usuário"><input name="username" minLength={3} maxLength={40} pattern="[A-Za-z0-9_-]+" placeholder="seu-nome" required autoComplete="username" /></FormField>}
        <FormField label="E-mail"><input name="email" type="email" placeholder="voce@email.com" required autoComplete="email" /></FormField>
        <FormField label="Senha"><input name="password" type="password" minLength={registering ? 10 : 1} placeholder={registering ? 'Pelo menos 10 caracteres' : 'Sua senha'} required autoComplete={registering ? 'new-password' : 'current-password'} /></FormField>
        {error && <div role="alert" className="form-error">{error}</div>}
        <Button type="submit" className="auth-submit" disabled={mutation.isPending}>{mutation.isPending ? 'Aguarde…' : registering ? 'Criar conta' : 'Entrar'} <ArrowRight size={16} /></Button>
      </form><div className="auth-switch">{registering ? 'Já tem uma conta?' : 'Ainda não tem conta?'} <button onClick={() => { setRegistering(!registering); setError('') }}>{registering ? 'Entrar' : 'Criar conta'}</button></div>
      {!registering && <div className="demo-login">Conta demonstrativa: <strong>demo@gametracker.local</strong> · Senha: <strong>GameTracker-demo-2026</strong></div>}
      <div className="auth-legal"><ShieldCheck size={14} /> Login seguro. Sem rastreamento de jogos em segundo plano.</div>
    </div></section>
  </div>
}
