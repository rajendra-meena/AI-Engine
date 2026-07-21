import React, { useState, useEffect } from 'react'
import { Brain, Sun, Moon, RefreshCw, BarChart3, Activity, Target } from 'lucide-react'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import useMarketStore from './store/useMarketStore'
import { isMarketOpen } from './utils/marketUtils'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './components/Dashboard'
import LivePage from './components/LivePage'
import BacktestResults from './components/BacktestResults'

function MarketStatusBadge() {
  const [open, setOpen] = useState(isMarketOpen())
  useEffect(() => {
    const id = setInterval(() => setOpen(isMarketOpen()), 60000)
    return () => clearInterval(id)
  }, [])
  return (
    <span className={`hidden sm:inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${
      open ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'
    }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${open ? 'bg-emerald-500 animate-pulse' : 'bg-gray-400'}`} />
      {open ? 'Open' : 'Closed'}
    </span>
  )
}

function Navbar({ page, setPage }) {
  const { selectedIndex, setSelectedIndex, indices, activePreset, setActivePreset, datePresets, triggerRefresh } = useMarketStore()
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-100/80 dark:border-gray-800/80 shadow-sm">
      <div className="max-w-none mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo */}
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-200 dark:shadow-blue-900/30 shrink-0">
              <Brain className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
            </div>
            <div className="hidden lg:block min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-lg font-bold text-gray-900 dark:text-white tracking-tight truncate">
                  Market<span className="gradient-text">Mind</span> AI
                </h1>
                <MarketStatusBadge />
              </div>
              <p className="hidden sm:block text-[10px] text-gray-400 dark:text-gray-500 -mt-0.5">Indian Market Analysis</p>
            </div>
          </div>

          {/* Right side controls */}
          <div className="flex items-center gap-1 sm:gap-2">
            

            

            {/* Index selector — only show on dashboard */}
            {page === 'dashboard' && (
              <select value={selectedIndex} onChange={(e) => setSelectedIndex(e.target.value)}
                className="px-2 sm:px-3 py-1.5 sm:py-2 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-lg text-[11px] sm:text-sm font-medium text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 transition-all cursor-pointer max-w-[90px] sm:max-w-none">
                {indices.map((idx) => <option key={idx.value} value={idx.value}>{idx.label}</option>)}
              </select>
            )}

            {/* Desktop date presets — only show on dashboard */}
            {page === 'dashboard' && (
              <div className="hidden sm:flex items-center gap-1.5">
                {datePresets.map((preset) => (
                  <button key={preset.label} onClick={() => { setActivePreset(preset.label) }}
                    className={`preset-btn ${activePreset === preset.label ? 'preset-btn-active' : 'preset-btn-inactive'}`}>
                    {preset.label}
                  </button>
                ))}
              </div>
            )}

             {/* Mobile date select — only on dashboard */}
            {page === 'dashboard' && (
              <select value={activePreset || 'Custom'} onChange={(e) => { setActivePreset(e.target.value) }}
                className="sm:hidden px-1.5 py-1.5 bg-white/80 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 rounded-lg text-[10px] font-medium text-gray-700 dark:text-gray-200 max-w-[60px]">
                {datePresets.map(p => <option key={p.label} value={p.label}>{p.label}</option>)}
              </select>
            )}

            {/* Refresh button — only show on dashboard */}
            {page === 'dashboard' && (
              <button onClick={triggerRefresh} className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 transition-all" aria-label="Refresh data">
                <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-600 dark:text-gray-300" />
              </button>
            )}

            {/* Page toggle — icon only on mobile */}
            <div className="flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
              <button onClick={() => setPage('dashboard')}
                className={`px-1.5 sm:px-2.5 py-1.5 text-[11px] font-medium transition-all flex items-center gap-1 ${
                  page === 'dashboard' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}>
                <BarChart3 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Daily</span>
              </button>
              <button onClick={() => setPage('live')}
                className={`px-1.5 sm:px-2.5 py-1.5 text-[11px] font-medium transition-all flex items-center gap-1 ${
                  page === 'live' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}>
                <Activity className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Live</span>
              </button>
              <button onClick={() => setPage('backtest')}
                className={`px-1.5 sm:px-2.5 py-1.5 text-[11px] font-medium transition-all flex items-center gap-1 ${
                  page === 'backtest' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-white dark:bg-gray-800 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}>
                <Target className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Backtest</span>
              </button>
            </div>

            {/* Theme toggle */}
            <button onClick={toggleTheme} className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center hover:bg-gray-200 dark:hover:bg-gray-700 transition-all" aria-label="Toggle theme">
              {theme === 'light' ? <Moon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-600" /> : <Sun className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-yellow-400" />}
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default function App() {
  const [page, setPage] = useState('dashboard')

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-100/50 to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 transition-colors duration-300">
        <Navbar page={page} setPage={setPage} />
        <main className="max-w-[1580px] mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6">
          <ErrorBoundary fallbackTitle="Dashboard error">
            {page === 'dashboard' ? <Dashboard /> : page === 'live' ? <LivePage /> : <BacktestResults />}
          </ErrorBoundary>
        </main>
      </div>
    </ThemeProvider>
  )
}
