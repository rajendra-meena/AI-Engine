import axios from 'axios'

const API = axios.create({ baseURL: '/api' })

export const savePrediction = async (predictionData) => {
  const resp = await API.post('/predictions', predictionData)
  return resp.data
}

export const getPredictions = async (params = {}) => {
  const resp = await API.get('/predictions', { params })
  return resp.data
}

export const getPredictionStats = async (symbol) => {
  const resp = await API.get('/predictions/stats', { params: symbol ? { symbol } : {} })
  return resp.data
}

export const checkResults = async () => {
  const resp = await API.post('/predictions/check-results')
  return resp.data
}

export const getPredictionById = async (id) => {
  const resp = await API.get(`/predictions/${id}`)
  return resp.data
}

export const deduplicatePredictions = async () => {
  const resp = await API.post('/predictions/cleanup')
  return resp.data
}

export const deletePrediction = async (id) => {
  const resp = await API.delete(`/predictions/${id}`)
  return resp.data
}
