// Saved dashboard conversations in localStorage.
import { logger } from './logger';

// ============ LOCALSTORAGE HELPERS ============
export const STORAGE_KEY = 'sticky-net-conversations';

export const loadConversations = () => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        logger.error('conversations load failed', { key: STORAGE_KEY, error: e });
        return [];
    }
};

export const saveConversations = (conversations) => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
        logger.error('conversations save failed', { key: STORAGE_KEY, count: conversations.length, error: e });
    }
};

export const generateId = () => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
