import { useState, useEffect, useCallback } from 'react'

export default function useTabWithHash(defaultTab = 'config') {
  const readHash = () => {
    const h = window.location.hash.replace('#', '')
    return h || defaultTab
  }

  const [activeTab, setActiveTabState] = useState(readHash)

  const setActiveTab = useCallback((tab) => {
    setActiveTabState(tab)
    window.history.replaceState(null, '', `#${tab}`)
  }, [])

  useEffect(() => {
    const onHashChange = () => setActiveTabState(readHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return [activeTab, setActiveTab]
}
