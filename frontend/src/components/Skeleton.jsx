import React from 'react'

export function Skeleton({ className = '' }) {
  return (
    <div className={`animate-pulse bg-gray-200 dark:bg-gray-700 rounded ${className}`} />
  )
}

export function StatsCardSkeleton() {
  return (
    <div className="stats-card">
      <Skeleton className="h-3 w-16 mb-2" />
      <Skeleton className="h-7 w-28" />
    </div>
  )
}

export function ChartSkeleton() {
  return (
    <div className="chart-container">
      <Skeleton className="h-4 w-28 mb-4" />
      <Skeleton className="h-[250px] sm:h-[350px] w-full rounded-lg" />
    </div>
  )
}

export function PredictionCardSkeleton() {
  return (
    <div className="ai-card">
      <div className="flex items-center gap-3 mb-4">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <div>
          <Skeleton className="h-4 w-32 mb-1" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>
      <Skeleton className="h-8 w-full mb-4" />
      <Skeleton className="h-12 w-full mb-4" />
      <Skeleton className="h-12 w-full mb-4" />
      <Skeleton className="h-16 w-full" />
    </div>
  )
}

export function SupportResistanceSkeleton() {
  return (
    <div className="pivot-card">
      <Skeleton className="h-4 w-24 mb-4" />
      {Array.from({ length: 7 }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full mb-1" />
      ))}
    </div>
  )
}