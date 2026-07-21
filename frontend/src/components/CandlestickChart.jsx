import React from 'react'

/**
 * Custom candlestick shape for Recharts Bar.
 *
 * Recharts passes x, y, width, height for the dataKey value (close).
 * We draw the high-low wick and the open-close body relative to the close position.
 *
 * Since Recharts doesn't pass the y-axis domain to custom shapes, we receive it
 * via the `domain` prop passed from the parent component.
 */
export function CandlestickShape({ x, y, width, height, payload, domain }) {
  if (!payload || !domain) return null
  const { open, close, high, low } = payload
  const isUp = close >= open
  const color = isUp ? '#22c55e' : '#ef4444'

  const [yMin, yMax] = domain
  const range = yMax - yMin || 1
  const chartArea = height
  const chartY = y

  const scale = (val) => chartY + chartArea - ((val - yMin) / range) * chartArea

  const openY = scale(open)
  const closeY = scale(close)
  const highY = scale(high)
  const lowY = scale(low)
  const candleWidth = Math.max(width * 0.6, 2)
  const candleX = x + (width - candleWidth) / 2
  const bodyTop = Math.min(openY, closeY)
  const bodyBottom = Math.max(openY, closeY)
  const bodyHeight = Math.max(bodyBottom - bodyTop, 1)

  return (
    <g>
      <line x1={x + width / 2} y1={highY} x2={x + width / 2} y2={lowY} stroke={color} strokeWidth={1} />
      <rect x={candleX} y={bodyTop} width={candleWidth} height={bodyHeight} fill={color} stroke={color} strokeWidth={0.5} rx={0.5} />
    </g>
  )
}