import { apiRequest, setStoredToken, getStoredToken } from './api';
function isUnauthorizedError(err) {
    if (!err || typeof err !== 'object')
        return false;
    const status = err.status;
    return status === 401;
}
async function fetchToken(email, password) {
    const params = new URLSearchParams();
    params.set('username', email);
    params.set('password', password);
    return apiRequest('/auth/login', {
        method: 'POST',
        body: params,
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
    });
}
export async function login(email, password) {
    const tokenResponse = await fetchToken(email, password);
    setStoredToken(tokenResponse.access_token);
    const user = await getCurrentUser();
    return { token: tokenResponse.access_token, user };
}
export async function register(email, password) {
    await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        headers: {
            'Content-Type': 'application/json',
        },
    });
    return login(email, password);
}
export async function getCurrentUser() {
    if (!getStoredToken())
        return null;
    try {
        return await apiRequest('/auth/me');
    }
    catch (err) {
        if (isUnauthorizedError(err)) {
            return null;
        }
        throw err;
    }
}
export function logout() {
    setStoredToken(null);
}
export async function changePassword(currentPassword, newPassword) {
    return apiRequest('/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
        }),
        headers: {
            'Content-Type': 'application/json',
        },
    });
}
