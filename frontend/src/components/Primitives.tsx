import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { LoaderCircle, Plus } from 'lucide-react'

export function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-title"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>
}

export function Panel({ title, action, children, className = '' }: { title?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{(title || action) && <div className="panel-heading">{title && <h2>{title}</h2>}{action}</div>}{children}</section>
}

export function Button({ children, variant = 'primary', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return <button className={`button button-${variant} ${props.className || ''}`} {...props}>{children}</button>
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-mark"><Plus size={18} /></div><h3>{title}</h3><p>{detail}</p>{action}</div>
}

export function LoadingState() { return <div className="loading-state"><LoaderCircle size={22} className="spin" /><span>Carregando seus dados…</span></div> }

export function ErrorState({ message = 'Não foi possível carregar os dados.', retry }: { message?: string; retry?: () => void }) {
  return <div className="error-state"><strong>Algo não saiu como esperado</strong><span>{message}</span>{retry && <Button variant="secondary" onClick={retry}>Tentar novamente</Button>}</div>
}

export function StatCard({ label, value, detail, icon }: { label: string; value: string | number; detail?: string; icon: ReactNode }) {
  return <div className="stat-card"><div className="stat-card-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong>{detail && <small>{detail}</small>}</div>
}

export function Cover({ src, name, className = '' }: { src?: string | null; name: string; className?: string }) {
  return <div className={`cover ${className}`}>{src ? <img src={src} alt={`Capa de ${name}`} loading="lazy" onError={(event) => { event.currentTarget.style.display = 'none' }} /> : <span>{name.split(' ').slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</span>}</div>
}

export function Progress({ value }: { value: number }) {
  return <div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></div>
}

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return <label className="form-field"><span>{label}</span>{children}</label>
}
