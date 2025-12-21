import { API_BASE } from '@/services/api'

export interface ApiResponse<T> {
  data: T
  status: number
  success?: boolean
  error?: string
}

export interface UseApi {
  get: <T>(path: string) => Promise<ApiResponse<T>>
  post: <T>(path: string, body: any) => Promise<ApiResponse<T>>
  put: <T>(path: string, body: any) => Promise<ApiResponse<T>>
  delete: <T>(path: string) => Promise<ApiResponse<T>>
}

/**
 * Build full API URL with base
 */
function buildApiUrl(path: string): string {
  const basePath = `${API_BASE || ''}`
  let fullUrl = `${basePath}${path}`.replace(/\/+/g, '/').replace('https:/', 'https://').replace('http:/', 'http://')

  // Handle the case where basePath is empty
  if (!basePath && !path.startsWith('http')) {
    fullUrl = path
  }

  return fullUrl
}

export function useApi(): UseApi {
  /**
   * GET request
   */
  const get = async <T>(path: string): Promise<ApiResponse<T>> => {
    const url = buildApiUrl(path)
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const error = new Error(`API Error: ${response.status} ${response.statusText}`)
      ;(error as any).response = { status: response.status, data }
      throw error
    }

    const data = (await response.json()) as T
    return {
      data,
      status: response.status,
      success: true,
    }
  }

  /**
   * POST request
   */
  const post = async <T>(path: string, body: any): Promise<ApiResponse<T>> => {
    const url = buildApiUrl(path)
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const error = new Error(`API Error: ${response.status} ${response.statusText}`)
      ;(error as any).response = { status: response.status, data }
      throw error
    }

    const data = (await response.json()) as T
    return {
      data,
      status: response.status,
      success: true,
    }
  }

  /**
   * PUT request
   */
  const put = async <T>(path: string, body: any): Promise<ApiResponse<T>> => {
    const url = buildApiUrl(path)
    const response = await fetch(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const error = new Error(`API Error: ${response.status} ${response.statusText}`)
      ;(error as any).response = { status: response.status, data }
      throw error
    }

    const data = (await response.json()) as T
    return {
      data,
      status: response.status,
      success: true,
    }
  }

  /**
   * DELETE request
   */
  const deleteRequest = async <T>(path: string): Promise<ApiResponse<T>> => {
    const url = buildApiUrl(path)
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      const error = new Error(`API Error: ${response.status} ${response.statusText}`)
      ;(error as any).response = { status: response.status, data }
      throw error
    }

    let data
    try {
      data = (await response.json()) as T
    } catch {
      data = null as any as T
    }

    return {
      data,
      status: response.status,
      success: true,
    }
  }

  return {
    get,
    post,
    put,
    delete: deleteRequest,
  }
}
