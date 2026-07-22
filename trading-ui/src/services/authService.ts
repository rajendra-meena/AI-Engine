/**
 * authService.ts
 *
 * Authentication service with JWT, OAuth, RBAC support.
 * All tokens are managed client-side with HTTP-only cookie preference.
 *
 * NO mock data — every call hits the backend auth endpoints.
 */

import apiClient from "@/lib/api"

/* ─── Types ─── */

export type UserRole = "admin" | "trader" | "viewer"
export type AuthProvider = "email" | "google" | "github"

export interface AuthUser {
  id: string
  email: string
  name: string
  role: UserRole
  avatar?: string | null
  emailVerified: boolean
  provider: AuthProvider
  createdAt: string
}

export interface LoginRequest {
  email: string
  password: string
  rememberMe?: boolean
}

export interface RegisterRequest {
  email: string
  password: string
  name: string
}

export interface AuthResponse {
  user: AuthUser
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface DeviceInfo {
  id: string
  name: string
  lastActive: string
  current: boolean
}

/* ─── Service ─── */

export const authService = {
  /** Login with email/password */
  async login(data: LoginRequest): Promise<AuthResponse> {
    const res = await apiClient.post("/api/auth/login", data)
    return res.data
  },

  /** Register a new account */
  async register(data: RegisterRequest): Promise<AuthResponse> {
    const res = await apiClient.post("/api/auth/register", data)
    return res.data
  },

  /** Logout — invalidate tokens */
  async logout(): Promise<void> {
    await apiClient.post("/api/auth/logout")
  },

  /** Refresh access token using refresh token */
  async refreshToken(token: string): Promise<AuthResponse> {
    const res = await apiClient.post("/api/auth/refresh", { refreshToken: token })
    return res.data
  },

  /** Get current user profile */
  async getProfile(): Promise<AuthUser> {
    const res = await apiClient.get("/api/auth/me")
    return res.data
  },

  /** Send forgot password email */
  async forgotPassword(email: string): Promise<void> {
    await apiClient.post("/api/auth/forgot-password", { email })
  },

  /** Reset password with token */
  async resetPassword(token: string, password: string): Promise<void> {
    await apiClient.post("/api/auth/reset-password", { token, password })
  },

  /** Verify email with token */
  async verifyEmail(token: string): Promise<void> {
    await apiClient.post("/api/auth/verify-email", { token })
  },

  /** Login with OAuth provider */
  async oAuthLogin(provider: "google" | "github", code: string): Promise<AuthResponse> {
    const res = await apiClient.post(`/api/auth/oauth/${provider}`, { code })
    return res.data
  },

  /** Send OTP for login */
  async sendOtp(email: string): Promise<void> {
    await apiClient.post("/api/auth/send-otp", { email })
  },

  /** Verify OTP and login */
  async verifyOtp(email: string, otp: string): Promise<AuthResponse> {
    const res = await apiClient.post("/api/auth/verify-otp", { email, otp })
    return res.data
  },

  /** Get active devices */
  async getDevices(): Promise<DeviceInfo[]> {
    const res = await apiClient.get("/api/auth/devices")
    return res.data
  },

  /** Revoke a device session */
  async revokeDevice(deviceId: string): Promise<void> {
    await apiClient.delete(`/api/auth/devices/${deviceId}`)
  },
}
