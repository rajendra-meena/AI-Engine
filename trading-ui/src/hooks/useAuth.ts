"use client"

import { useCallback, useEffect } from "react"
import { useAuthStore } from "@/store/useAuthStore"
import { authService } from "@/services/authService"
import apiClient from "@/lib/api"

/**
 * useAuth — handles authentication lifecycle, token refresh, and RBAC.
 */
export function useAuth() {
  const store = useAuthStore()

  // Auto-refresh token on mount if we have a refresh token
  useEffect(() => {
    if (store.refreshToken && !store.user) {
      store.setStatus("loading")
      authService.refreshToken(store.refreshToken)
        .then((res) => store.setAuth(res))
        .catch(() => store.clearAuth())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Attach auth interceptor to axios
  useEffect(() => {
    const interceptor = apiClient.interceptors.request.use((config) => {
      const token = useAuthStore.getState().accessToken
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true
          const refreshToken = useAuthStore.getState().refreshToken
          if (refreshToken) {
            try {
              const res = await authService.refreshToken(refreshToken)
              store.updateTokens(res.accessToken, res.refreshToken)
              originalRequest.headers.Authorization = `Bearer ${res.accessToken}`
              return apiClient(originalRequest)
            } catch {
              store.clearAuth()
            }
          }
        }
        return Promise.reject(error)
      }
    )

    return () => {
      apiClient.interceptors.request.eject(interceptor)
      apiClient.interceptors.response.eject(responseInterceptor)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = useCallback(async (email: string, password: string, rememberMe = false) => {
    store.setStatus("loading")
    try {
      const res = await authService.login({ email, password, rememberMe })
      store.setAuth(res, rememberMe)
      return res
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      store.setError(err.response?.data?.detail || err.message || "Login failed")
      store.setStatus("error")
      throw e
    }
  }, [store])

  const register = useCallback(async (email: string, password: string, name: string) => {
    store.setStatus("loading")
    try {
      const res = await authService.register({ email, password, name })
      store.setAuth(res)
      return res
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      store.setError(err.response?.data?.detail || err.message || "Registration failed")
      store.setStatus("error")
      throw e
    }
  }, [store])

  const logout = useCallback(async () => {
    try { await authService.logout() } catch {}
    store.clearAuth()
  }, [store])

  return {
    user: store.user,
    status: store.status,
    error: store.error,
    isAuthenticated: store.status === "authenticated",
    isAdmin: store.hasRole("admin"),
    isTrader: store.hasRole(["admin", "trader"]),
    login,
    register,
    logout,
    clearError: () => store.setError(null),
  }
}
