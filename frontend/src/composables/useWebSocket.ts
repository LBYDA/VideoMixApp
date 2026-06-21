import { onUnmounted, ref } from 'vue'

export function useWebSocket() {
  const connected = ref(false)
  const message = ref<any>(null)
  let ws: WebSocket | null = null

  function connect(jobId: string) {
    disconnect()

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${protocol}//${location.host}/ws/progress/${jobId}`)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (evt) => {
      try {
        message.value = JSON.parse(evt.data)
      } catch { /* ignore */ }
    }

    ws.onclose = () => {
      connected.value = false
    }

    ws.onerror = () => {
      connected.value = false
    }
  }

  function send(data: any) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  onUnmounted(disconnect)

  return { connected, message, connect, send, disconnect }
}
