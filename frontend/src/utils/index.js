// Export API utilities
export * from './api';
// Utility functions
export const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
    };
};
export const throttle = (func, limit) => {
    let inThrottle = false;
    return (...args) => {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => (inThrottle = false), limit);
        }
    };
};
// Format utilities
export const formatOvers = (balls) => {
    const overs = Math.floor(balls / 6);
    const remainingBalls = balls % 6;
    return remainingBalls === 0 ? `${overs}` : `${overs}.${remainingBalls}`;
};
export const formatScore = (runs, wickets) => {
    return `${runs}/${wickets}`;
};
// Validation utilities
export const isValidUUID = (uuid) => {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
};
export const isValidPlayerName = (name) => {
    return name.trim().length >= 2 && name.trim().length <= 50;
};
export const isValidTeamName = (name) => {
    return name.trim().length >= 2 && name.trim().length <= 30;
};
// Date utilities
export const formatDate = (date) => {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
};
// Local storage utilities
export const storage = {
    get: (key, defaultValue) => {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        }
        catch {
            return defaultValue;
        }
    },
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        }
        catch (error) {
            console.warn('Failed to save to localStorage:', error);
        }
    },
    remove: (key) => {
        try {
            localStorage.removeItem(key);
        }
        catch (error) {
            console.warn('Failed to remove from localStorage:', error);
        }
    }
};
// Error handling utilities
export const handleApiError = (error) => {
    if (error instanceof Error) {
        return error.message;
    }
    if (typeof error === 'string') {
        return error;
    }
    return 'An unexpected error occurred';
};
// Constants
export const CRICKET_CONSTANTS = {
    BALLS_PER_OVER: 6,
    MAX_OVERS_25: 25,
    MAX_WICKETS: 10,
    MIN_PLAYERS_PER_TEAM: 4,
    MAX_PLAYERS_PER_TEAM: 15
};
