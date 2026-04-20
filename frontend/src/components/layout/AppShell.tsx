import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { DashboardPage } from '../../pages/DashboardPage'
import { UploadPage } from '../../pages/UploadPage'
import { QueryPage } from '../../pages/QueryPage'

const ROUTES = ['/', '/upload', '/query'] as const
type AppRoute = typeof ROUTES[number]

function pageFor(route: AppRoute) {
  if (route === '/') return <DashboardPage />
  if (route === '/upload') return <UploadPage />
  return <QueryPage />
}

export function AppShell() {
  const location = useLocation()
  // Track which routes have ever been visited so we only mount them once
  const [everMounted, setEverMounted] = useState<Set<string>>(
    () => new Set([location.pathname])
  )

  useEffect(() => {
    setEverMounted(prev => {
      if (prev.has(location.pathname)) return prev
      return new Set([...prev, location.pathname])
    })
  }, [location.pathname])

  return (
    <div className="min-h-screen bg-deep bg-neural">
      <Sidebar />
      <main className="ml-16 lg:ml-56 min-h-screen">
        {ROUTES.map(route => {
          const active = location.pathname === route
          if (!everMounted.has(route)) return null
          return (
            <div
              key={route}
              style={{ display: active ? 'block' : 'none' }}
              aria-hidden={!active}
            >
              {pageFor(route)}
            </div>
          )
        })}
      </main>

      {/* Ambient background orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-violet-600/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-cyan-600/5 rounded-full blur-3xl" />
      </div>
    </div>
  )
}
