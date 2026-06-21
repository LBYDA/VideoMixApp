import { ref } from 'vue'
import axios from 'axios'
import type { FileTreeItem } from '@/types/api'

export function useFileTree() {
  const items = ref<FileTreeItem[]>([])
  const loading = ref(false)

  async function load(path: string = '') {
    loading.value = true
    try {
      const { data } = await axios.get('/api/files/tree', { params: { path } })
      items.value = data
    } catch (e) {
      console.error('Failed to load file tree:', e)
      items.value = []
    } finally {
      loading.value = false
    }
  }

  return { items, loading, load }
}
