import { useEffect, useState, useRef } from 'react'

interface NumberTickerProps {
  value: number
  decimalPlaces?: number
  duration?: number
  prefix?: string
  suffix?: string
  className?: string
}

function isReducedMotion(): boolean {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  )
}

export function NumberTicker({
  value,
  decimalPlaces = 0,
  duration = 500,
  prefix = '',
  suffix = '',
  className = '',
}: NumberTickerProps) {
  const [displayValue, setDisplayValue] = useState<number>(() => value)
  const previousValueRef = useRef<number>(value)

  useEffect(() => {
    if (isReducedMotion()) {
      return
    }

    const startVal = previousValueRef.current
    const endVal = value
    if (startVal === endVal) {
      return
    }

    let startTime: number | null = null
    let animFrame: number | null = null

    const step = (timestamp: number) => {
      if (startTime === null) {
        startTime = timestamp
      }
      const elapsed = timestamp - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easeProgress = 1 - Math.pow(1 - progress, 3)
      const current = startVal + (endVal - startVal) * easeProgress

      setDisplayValue(current)

      if (progress < 1) {
        animFrame = requestAnimationFrame(step)
      } else {
        setDisplayValue(endVal)
        previousValueRef.current = endVal
      }
    }

    animFrame = requestAnimationFrame(step)

    return () => {
      if (animFrame !== null) {
        cancelAnimationFrame(animFrame)
      }
    }
  }, [value, duration])

  const renderedValue = isReducedMotion() ? value : displayValue

  return (
    <span className={className}>
      {prefix}
      {renderedValue.toLocaleString('vi-VN', {
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces,
      })}
      {suffix}
    </span>
  )
}
