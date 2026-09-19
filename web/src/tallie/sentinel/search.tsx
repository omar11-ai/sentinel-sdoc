import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

type SearchState = { searchQuery: string; setSearchQuery: (q: string) => void }

const SearchContext = createContext<SearchState | null>(null)

export function SearchProvider({ children }: { children: ReactNode }) {
  const [searchQuery, setSearchQuery] = useState('')
  const value = useMemo(() => ({ searchQuery, setSearchQuery }), [searchQuery])
  return <SearchContext.Provider value={value}>{children}</SearchContext.Provider>
}

export function useGlobalSearch() {
  const ctx = useContext(SearchContext)
  if (!ctx) throw new Error('useGlobalSearch must be used within SearchProvider')
  return ctx
}
