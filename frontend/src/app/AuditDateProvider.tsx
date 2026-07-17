import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useLocation } from 'react-router-dom'
import { readAuditDate } from '../shared/date/auditDate'
import { AuditDateContext } from '../shared/date/auditDateStore'

export function AuditDateProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const urlDate = readAuditDate(location.search)
  const [rememberedDate, setRememberedDate] = useState(urlDate)

  useEffect(() => {
    if (urlDate) setRememberedDate(urlDate)
  }, [urlDate])

  const rememberDate = useCallback((date: string) => {
    if (date) setRememberedDate(date)
  }, [])
  const date = urlDate || rememberedDate
  const value = useMemo(() => ({ date, rememberDate }), [date, rememberDate])

  return (
    <AuditDateContext.Provider value={value}>
      {children}
    </AuditDateContext.Provider>
  )
}
