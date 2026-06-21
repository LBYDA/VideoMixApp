<template>
  <div class="file-picker">
    <div class="picker-header">
      <span class="picker-label">{{ label }}</span>
      <button class="btn btn-sm" @click="goUp" v-if="currentPath">上一级</button>
    </div>
    <div class="picker-list" v-if="!loading">
      <div
        v-for="item in items"
        :key="item.path"
        class="picker-item"
        :class="{ selected: isSelected(item.path) }"
        @click="select(item)"
      >
        <span class="item-icon">{{ item.is_dir ? '📁' : '🎬' }}</span>
        <span class="item-name">{{ item.name }}</span>
      </div>
      <div v-if="items.length === 0" class="empty">目录为空</div>
    </div>
    <div v-else class="loading">加载中...</div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import type { FileTreeItem } from '@/types/api'

const props = withDefaults(defineProps<{
  label?: string
  modelValue?: string | string[]
  multiple?: boolean
  foldersOnly?: boolean
}>(), {
  label: '选择文件',
  multiple: false,
  foldersOnly: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | string[]]
}>()

const items = ref<FileTreeItem[]>([])
const loading = ref(false)
const currentPath = ref('')

async function load(path: string = '') {
  loading.value = true
  try {
    const { data } = await axios.get('/api/files/tree', { params: { path } })
    items.value = props.foldersOnly
      ? data.filter((f: FileTreeItem) => f.is_dir)
      : data
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

function select(item: FileTreeItem) {
  if (item.is_dir) {
    currentPath.value = item.path
    load(item.path)
  } else if (!props.foldersOnly) {
    if (props.multiple) {
      const current = Array.isArray(props.modelValue) ? [...props.modelValue] : []
      const idx = current.indexOf(item.path)
      if (idx >= 0) {
        current.splice(idx, 1)
      } else {
        current.push(item.path)
      }
      emit('update:modelValue', current)
    } else {
      emit('update:modelValue', item.path)
    }
  }
}

function goUp() {
  const parent = currentPath.value.split('/').slice(0, -1).join('/') || ''
  currentPath.value = parent
  load(parent)
}

function isSelected(path: string) {
  if (props.multiple && Array.isArray(props.modelValue)) {
    return props.modelValue.includes(path)
  }
  return props.modelValue === path
}

onMounted(() => load())
</script>

<style scoped>
.file-picker {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-primary);
}

.picker-label {
  font-size: 13px;
  font-weight: 600;
}

.picker-list {
  max-height: 250px;
  overflow-y: auto;
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}

.picker-item:hover {
  background: var(--bg-primary);
}

.picker-item.selected {
  background: rgba(74, 144, 217, 0.1);
  border-left: 3px solid var(--accent);
}

.item-icon {
  width: 24px;
}

.item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty, .loading {
  padding: 20px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}
</style>
