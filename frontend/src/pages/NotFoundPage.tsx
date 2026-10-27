import { Link } from 'react-router-dom'
import { ArrowLeft, SearchX } from 'lucide-react'
import { Button } from '../components/Primitives'

export default function NotFoundPage() {
  return <div className="not-found"><span className="not-found-icon"><SearchX size={25} /></span><span className="eyebrow">ERRO 404</span><h1>Esta página não existe.</h1><p>O endereço pode estar incorreto ou o conteúdo foi removido.</p><Link to="/"><Button><ArrowLeft size={15} /> Voltar ao início</Button></Link></div>
}
