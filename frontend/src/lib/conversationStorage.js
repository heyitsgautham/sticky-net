// Saved dashboard conversations in localStorage.
// ============ LOCALSTORAGE HELPERS ============
export const STORAGE_KEY = 'sticky-net-conversations';

export const loadConversations = () => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        console.error('Failed to load conversations:', e);
        return [];
    }
};

export const saveConversations = (conversations) => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch (e) {
        console.error('Failed to save conversations:', e);
    }
};

export const generateId = () => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
