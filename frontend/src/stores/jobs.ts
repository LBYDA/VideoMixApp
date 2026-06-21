import { defineStore } from 'pinia'
import axios from 'axios'
import type { JobProgress } from '@/types/api'

export const useJobsStore = defineStore('jobs', {
  state: () => ({
    activeJob: null as JobProgress | null,
    jobHistory: [] as JobProgress[],
  }),

  actions: {
    setActive(job: JobProgress | null) {
      this.activeJob = job
    },

    async fetchHistory(status?: string) {
      try {
        const { data } = await axios.get('/api/jobs', {
          params: { status, limit: 50 },
        })
        this.jobHistory = data
      } catch (e) {
        console.error('Failed to fetch jobs:', e)
      }
    },

    async fetchJob(type: string, jobId: string): Promise<JobProgress | null> {
      try {
        const { data } = await axios.get(`/api/${type}/job/${jobId}`)
        return data
      } catch {
        return null
      }
    },
  },
})
