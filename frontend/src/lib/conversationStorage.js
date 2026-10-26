// Saved dashboard conversations in localStorage.
import { logger } from "./logger";

// ============ LOCALSTORAGE HELPERS ============
export const STORAGE_KEY = "sticky-net-conversations";

// A saved conversation the dashboard can render: an object with an id and a message list.
export const isSavedConversation = (value) =>
  Boolean(value) &&
  typeof value === "object" &&
  typeof value.id === "string" &&
  Array.isArray(value.messages);

// Saved conversations, or [] when storage is empty or holds something else.
// Anything the dashboard cannot render is dropped, since one bad entry from an
// older build or a manual edit would otherwise blank the whole page.
export const loadConversations = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) {
      logger.warn("conversations ignored", { key: STORAGE_KEY, reason: "not an array" });
      return [];
    }
    const valid = parsed.filter(isSavedConversation);
    if (valid.length < parsed.length) {
      logger.warn("conversations dropped", {
        key: STORAGE_KEY,
        dropped: parsed.length - valid.length,
      });
    }
    return valid;
  } catch (e) {
    logger.error("conversations load failed", { key: STORAGE_KEY, error: e });
    return [];
  }
};

export const saveConversations = (conversations) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (e) {
    logger.error("conversations save failed", {
      key: STORAGE_KEY,
      count: conversations.length,
      error: e,
    });
  }
};

export const generateId = () => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
