import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import { format, subDays } from 'date-fns'
import useMarketStore from '../store/useMarketStore'

export function useMarketData() {
  const {
    selectedIndex,
    activePreset,
    customStartDate,
    customEndDate,
    refreshTrigger,
    setFullDataAndSlice,
    setLoading,
    setError,
  } = useMarketStore()

  const [cacheInfo, setCacheInfo] = useState(null)
  const fetchedRef = useRef({}) // track which symbols we've fetched

  const fetchCacheInfo = useCallback(async () => {
    try {
      const resp = await axios.get('/api/cache/status', {
        params: { symbol: selectedIndex },
      })
      if (resp.data) setCacheInfo(resp.data)
    } catch {
      // silent
    }
  }, [selectedIndex])

  const fetchData = useCallback(async (force = false) => {
    // Skip fetch if we already have data for this symbol (unless forced)
    const state = useMarketStore.getState()
    if (!force && state.fullData.length > 0 && fetchedRef.current[state.selectedIndex]) {
      // Still update the slice in case preset changed
      state.sliceData()
      return
    }

    setLoading(true)
    setError(null)

    try {
      const endDate = new Date()
      const startDate = subDays(endDate, 200)

      const params = {
        symbol: state.selectedIndex,
        start: format(startDate, 'yyyy-MM-dd'),
        end: format(endDate, 'yyyy-MM-dd'),
      }

      const response = await axios.get('/api/data', { params })

      if (response.data && response.data.data) {
        const sorted = [...response.data.data].sort(
          (a, b) => new Date(a.Date) - new Date(b.Date)
        )
        fetchedRef.current[state.selectedIndex] = true
        useMarketStore.getState().setFullDataAndSlice(sorted)
      } else {
        useMarketStore.getState().setFullDataAndSlice([])
      }

      fetchCacheInfo()
    } catch (err) {
      console.error('Error fetching market data:', err)
      setError(err.message || 'Failed to fetch data')
      useMarketStore.getState().setFullDataAndSlice([])
    } finally {
      setLoading(false)
    }
  }, [selectedIndex, fetchCacheInfo])

  // Initial fetch — skip if data already loaded for this symbol
  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Re-fetch when refreshTrigger changes (manual refresh button) — force
  useEffect(() => {
    if (refreshTrigger > 0) fetchData(true)
  }, [refreshTrigger, fetchData])

  // Auto-refresh during market hours: poll every 90s between 9:15-15:30 IST
  useEffect(() => {
    const checkAndRefresh = () => {
      const now = new Date()
      const utc = now.getTime() + now.getTimezoneOffset() * 60000
      const ist = new Date(utc + 5.5 * 3600000)
      const totalMin = ist.getHours() * 60 + ist.getMinutes()
      const isMarketDay = ist.getDay() !== 0 && ist.getDay() !== 6
      const isMarketOpen = isMarketDay && totalMin >= 555 && totalMin < 930
      if (isMarketOpen) fetchData(true)
    }
    const id = setInterval(checkAndRefresh, 90000)
    return () => clearInterval(id)
  }, [fetchData])

  // Re-slice when preset/custom range changes
  useEffect(() => {
    useMarketStore.getState().sliceData()
  }, [activePreset, customStartDate, customEndDate])

  return {
    data: useMarketStore(state => state.data),
    loading: useMarketStore(state => state.loading),
    error: useMarketStore(state => state.error),
    refetch: () => fetchData(true),
    cacheInfo,
  }
}
