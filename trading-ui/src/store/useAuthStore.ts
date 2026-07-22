import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { AuthUser, UserRole, AuthResponse } from "@/services/authService"

/* ─── Types ─── */

export type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated" | "error"

interface AuthState {
  user: AuthUser | null
  status: AuthStatus
  accessToken: string | null
  refreshToken: string | null
  error: string | null
  rememberMe: boolean

  setAuth: (response: AuthResponse, remember?: boolean) => void
  setUser: (user: AuthUser) => void
  setStatus: (status: AuthStatus) => void
  setError: (error: string | null) => void
  setRememberMe: (remember: boolean) => void
  updateTokens: (accessToken: string, refreshToken: string) => void
  clearAuth: () => void
  hasRole: (roles: UserRole | UserRole[]) => boolean
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      status: "idle",
      accessToken: null,
      refreshToken: null,
      error: null,
      rememberMe: false,

      setAuth: (response, remember = false) =>
        set({
          user: response.user,
          accessToken: response.accessToken,
          refreshToken: response.refreshToken,
          status: "authenticated",
          error: null,
          rememberMe: remember,
        }),

      setUser: (user) => set({ user }),
      setStatus: (status) => set({ status }),
      setError: (error) => set({ error }),
      setRememberMe: (rememberMe) => set({ rememberMe }),

      updateTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),

      clearAuth: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          status: "unauthenticated",
          error: null,
        }),

      hasRole: (roles) => {
        const user = get().user
        if (!user) return false
        const allowed = Array.isArray(roles) ? roles : [roles]
        return allowed.includes(user.role)
      },

      logout: () => {
        get().clearAuth()
      },
    }),
    {
      name: "marketmind-auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        rememberMe: state.rememberMe,
      }),
    }
  )
)
