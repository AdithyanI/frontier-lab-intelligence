import { createContext, useContext } from 'react'
import { withAuditDate } from './auditDate'

export interface AuditDateContextValue {
  date: string
  rememberDate: (date: string) => void
}

export const AuditDateContext = createContext<AuditDateContextValue | null>(null)

export function useAuditDate(): AuditDateContextValue {
  const value = useContext(AuditDateContext)
  if (!value) throw new Error('useAuditDate must be used inside AuditDateProvider')
  return value
}

export function useAuditDatePath(path: string): string {
  const { date } = useAuditDate()
  return withAuditDate(path, date)
}
