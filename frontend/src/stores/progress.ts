import { defineStore } from 'pinia'
import type { JobProgress } from '@/types/api'
import type { LogEntry } from '@/types/models'

export const useProgressStore = defineStore('progress', {
  state: () => ({
    connected: false,
    currentJob: null as JobProgress | null,
    logs: [] as LogEntry[],
    ws: null as WebSocket | null,
    cancelRequested: false,
  }),

  actions: {
    connect(jobId: string) {
      this.disconnect()

      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${location.host}/ws/progress/${jobId}`

      this.ws = new WebSocket(wsUrl)
      this.logs = []
      this.cancelRequested = false

      this.ws.onopen = () => {
        this.connected = true
      }

      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          const { event, data } = msg

          switch (event) {
            case 'connected':
              break
            case 'progress':
              this.currentJob = data as JobProgress
              break
            case 'log':
              this.logs.push({
                level: data.level || 'info',
                message: data.message,
                timestamp: Date.now(),
              })
              // 最多保留 200 条日志
              if (this.logs.length > 200) {
                this.logs.shift()
              }
              break
            case 'completed':
              this.currentJob = data as JobProgress
              break
            case 'error':
              this.currentJob = data as JobProgress
              break
          }
        } catch { /* ignore */ }
      }

      this.ws.onclose = () => {
        this.connected = false
      }

      this.ws.onerror = () => {
        this.connected = false
      }
    },

    disconnect() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this.connected = false
    },

    cancelJob() {
      this.cancelRequested = true
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ action: 'cancel' }))
      }
    },
  },
})
