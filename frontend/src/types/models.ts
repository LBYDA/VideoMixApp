export interface LogEntry {
  level: 'info' | 'warn' | 'error'
  message: string
  timestamp: number
}
