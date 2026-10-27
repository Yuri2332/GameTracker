export type Game = {
  id: string; game_id: string; name: string; cover_url: string | null; description: string | null
  developer?: string | null; publisher?: string | null; release_date?: string | null; platform: string
  genre: string | null; status: 'backlog' | 'playing' | 'paused' | 'completed'; rating: number | null
  favorite: boolean; tags: string[]; personal_notes?: string | null; total_played_hours: number
  last_session_at: string | null; created_at: string
}

export type Session = {
  id: string; game_id: string; game_name: string; cover_url: string | null; started_at: string
  ended_at: string | null; duration_seconds: number; duration_hours: number; source: string; note: string | null; state: string
  paused_seconds?: number
}

export type Goal = {
  id: string; title: string; description: string | null; goal_type: string; target: number
  progress: number; percentage: number; deadline: string | null; status: string; game_ids: string[]
}

export type User = { id: string; email: string; username: string; avatar_url: string | null; created_at: string }

export type DashboardData = {
  totals: { games: number; hours: number; week_hours: number; sessions: number; most_played: { name: string; hours: number } | null }
  weekly_goal: { target: number; progress: number; percentage: number }
  activity: { date: string; hours: number }[]; monthly_hours: number
  recent_games: Game[]; favorites: Game[]; recent_sessions: Session[]; goals: Goal[]
}
