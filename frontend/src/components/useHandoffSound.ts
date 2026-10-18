import { useCallback, useEffect, useRef, useState } from 'react'

/** Reuse one context, unlocked inside a real user gesture. Queue every delivery. */
export function useHandoffSound(enabled: boolean) {
  const context = useRef<AudioContext | null>(null)
  const pending = useRef(0)
  const timer = useRef<number | undefined>()
  const [ready, setReady] = useState(false)

  const drain = useCallback(function next() {
    const audio = context.current
    if (!audio || audio.state !== 'running' || pending.current === 0) return
    pending.current -= 1
    const start = audio.currentTime
    for (const [index, frequency] of [880, 1174.7].entries()) {
      const at = start + index * 0.18
      const oscillator = audio.createOscillator()
      const gain = audio.createGain()
      oscillator.frequency.value = frequency
      gain.gain.setValueAtTime(0.0001, at)
      gain.gain.exponentialRampToValueAtTime(0.18, at + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.3)
      oscillator.connect(gain)
      gain.connect(audio.destination)
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect() }
      oscillator.start(at)
      oscillator.stop(at + 0.32)
    }
    timer.current = window.setTimeout(() => {
      timer.current = undefined
      next()
    }, 650)
  }, [])

  const enable = useCallback(async () => {
    try {
      const Audio = window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!Audio) return
      if (!context.current || context.current.state === 'closed') {
        context.current = new Audio()
        context.current.onstatechange = () => setReady(context.current?.state === 'running')
      }
      await context.current.resume()
      setReady(context.current.state === 'running')
      if (timer.current === undefined) drain()
    } catch {
      setReady(false)
    }
  }, [drain])

  const enqueue = useCallback((count: number) => {
    pending.current += count
    if (timer.current === undefined) drain()
  }, [drain])

  useEffect(() => {
    if (!enabled) return
    const unlock = () => { void enable() }
    window.addEventListener('pointerdown', unlock)
    window.addEventListener('keydown', unlock)
    return () => {
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
      window.clearTimeout(timer.current)
      timer.current = undefined
      pending.current = 0
      if (context.current) {
        context.current.onstatechange = null
        void context.current.close()
        context.current = null
      }
    }
  }, [enabled, enable])

  return { ready, enable, enqueue }
}
