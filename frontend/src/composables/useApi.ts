import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,  // 5 min for large requests
})

export function useApi() {
  return { api }
}
