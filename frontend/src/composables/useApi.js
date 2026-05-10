import { API_BASE } from '@/services/api';
/**
 * Build full API URL with base
 */
function buildApiUrl(path) {
    const basePath = `${API_BASE || ''}`;
    let fullUrl = `${basePath}${path}`.replace(/\/+/g, '/').replace('https:/', 'https://').replace('http:/', 'http://');
    // Handle the case where basePath is empty
    if (!basePath && !path.startsWith('http')) {
        fullUrl = path;
    }
    return fullUrl;
}
export function useApi() {
    /**
     * GET request
     */
    const get = async (path) => {
        const url = buildApiUrl(path);
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            const error = new Error(`API Error: ${response.status} ${response.statusText}`);
            error.response = { status: response.status, data };
            throw error;
        }
        const data = (await response.json());
        return {
            data,
            status: response.status,
            success: true,
        };
    };
    /**
     * POST request
     */
    const post = async (path, body) => {
        const url = buildApiUrl(path);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            const error = new Error(`API Error: ${response.status} ${response.statusText}`);
            error.response = { status: response.status, data };
            throw error;
        }
        const data = (await response.json());
        return {
            data,
            status: response.status,
            success: true,
        };
    };
    /**
     * PUT request
     */
    const put = async (path, body) => {
        const url = buildApiUrl(path);
        const response = await fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            const error = new Error(`API Error: ${response.status} ${response.statusText}`);
            error.response = { status: response.status, data };
            throw error;
        }
        const data = (await response.json());
        return {
            data,
            status: response.status,
            success: true,
        };
    };
    /**
     * DELETE request
     */
    const deleteRequest = async (path) => {
        const url = buildApiUrl(path);
        const response = await fetch(url, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            const error = new Error(`API Error: ${response.status} ${response.statusText}`);
            error.response = { status: response.status, data };
            throw error;
        }
        let data;
        try {
            data = (await response.json());
        }
        catch {
            data = null;
        }
        return {
            data,
            status: response.status,
            success: true,
        };
    };
    return {
        get,
        post,
        put,
        delete: deleteRequest,
    };
}
