// Copyright (c) 2024 Ameya Chopade. Licensed under Apache-2.0 with Commons Clause.
// Commercial use and cloud deployment as a service are strictly prohibited.
// See LICENSE.md for full terms.
import { useEffect, useState } from 'react'
import { LoginView } from '@/components/LoginView'
import { DashboardView } from '@/components/DashboardView'
import { UsernameView } from '@/components/UsernameView'
import { LoadingScreen } from '@/components/LoadingScreen'
import { getBackendConfig, authenticate } from '@/lib/github-api'
import type { AuthResult, RepoTraffic } from '@/lib/github-api'
import type { PublicProfile, PublicRepo } from '@/lib/github-public'
import { fetchUsernamePayload } from '@/lib/github-public'

const STORAGE_KEY = 'gh-traffic-session'

type Session =
  | { mode: 'api'; auth: AuthResult; token: string }
  | { mode: 'csv'; data: RepoTraffic[] }
  | { mode: 'username'; profile: PublicProfile; repos: PublicRepo[] }

export function DashboardPage() {
  const [session, setSession] = useState<Session | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    // Auto-load username mode if ?user= is in the URL
    try {
      const params = new URLSearchParams(window.location.search)
      const userParam = params.get('user')
      if (userParam) {
        // Trigger username fetch on load
        fetchUsernamePayload(userParam).then(({ profile, repos }) => {
          setSession({ mode: 'username', profile, repos })
        }).catch(() => {
          /* ignore — fall through to login */
        }).finally(() => setReady(true))
        return
      }
    } catch { /* ignore */ }

    let existingSession: Session | null = null
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY)
      if (raw) existingSession = JSON.parse(raw)
    } catch { /* ignore */ }

    if (existingSession) {
      setSession(existingSession)
      setReady(true)
      return
    }

    getBackendConfig()
      .then((cfg) => {
        if (cfg.has_token) {
          authenticate("")
            .then((auth) => {
              setSession({ mode: "api", auth, token: "" })
            })
            .catch(() => {
              /* ignore */
            })
            .finally(() => setReady(true))
        } else {
          setReady(true)
        }
      })
      .catch(() => {
        setReady(true)
      })
  }, [])

  function persist(s: Session) {
    setSession(s)
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s)) } catch { /* ignore quota */ }
  }

  function handleApiSuccess(auth: AuthResult, token: string) {
    persist({ mode: 'api', auth, token })
  }

  function handleCsvSuccess(data: RepoTraffic[]) {
    persist({ mode: 'csv', data })
  }

  function handleUsernameSuccess(profile: PublicProfile, repos: PublicRepo[]) {
    persist({ mode: 'username', profile, repos })
    try {
      const url = new URL(window.location.href)
      url.searchParams.set('user', profile.login)
      window.history.replaceState(null, '', url.toString())
    } catch { /* ignore */ }
  }

  function handleLogout() {
    setSession(null)
    sessionStorage.removeItem(STORAGE_KEY)
    try {
      const url = new URL(window.location.href)
      url.searchParams.delete('user')
      window.history.replaceState(null, '', url.toString())
    } catch { /* ignore */ }
  }

  if (!ready) {
    return <LoadingScreen label="Connecting your account…" durationMs={25000} />
  }

  if (!session) {
    return (
      <LoginView
        onApiSuccess={handleApiSuccess}
        onCsvSuccess={handleCsvSuccess}
        onUsernameSuccess={handleUsernameSuccess}
      />
    )
  }

  if (session.mode === 'username') {
    return (
      <UsernameView
        profile={session.profile}
        repos={session.repos}
        onLogout={handleLogout}
      />
    )
  }

  return <DashboardView source={session} onLogout={handleLogout} />
}
