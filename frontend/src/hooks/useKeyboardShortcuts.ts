import { useEffect } from 'react'

type KeyMap = Record<string, () => void>

export function useKeyboardShortcuts(shortcuts: KeyMap) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      const key = [
        e.metaKey || e.ctrlKey ? 'mod' : '',
        e.shiftKey ? 'shift' : '',
        e.altKey ? 'alt' : '',
        e.key.toLowerCase(),
      ].filter(Boolean).join('+')

      if (shortcuts[key]) {
        e.preventDefault()
        shortcuts[key]()
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [shortcuts])
}
