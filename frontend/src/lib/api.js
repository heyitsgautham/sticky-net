// Client for the Sticky-Net API. REACT_APP_* values are baked in at build time.
import { MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS } from "./limits";
import { parseAnalyzeDetailed } from "./schemas";

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

export const API_KEY = process.env.REACT_APP_API_KEY || 'test-api-key';

// True when GET /health answers 2xx.
export async function checkHealth(fetchImpl = fetch) {
    try {
        const response = await fetchImpl(`${API_BASE_URL}/health`, { method: 'GET' });
        return response.ok;
    } catch {
        return false;
    }
}

// Turn dashboard messages into the API's conversationHistory entries.
// Only the most recent MAX_HISTORY_MESSAGES go, each cut to MAX_MESSAGE_CHARS, so a
// long chat keeps getting real analyses instead of the API's fallback reply.
export const toConversationHistory = (messages) =>
    messages.slice(-MAX_HISTORY_MESSAGES).map((m) => ({
        sender: m.sender,
        text: (m.text || "").slice(0, MAX_MESSAGE_CHARS),
        timestamp: m.isoTimestamp || new Date().toISOString(),
    }));

// POST one scammer message to /api/v1/analyze/detailed and return the validated body.
// Throws on a non-2xx status, so the caller can mark the API offline, and throws
// ApiResponseError when the body does not match the API's response schema.
export async function analyzeDetailed(
    { text, timestamp, history, channel, locale },
    fetchImpl = fetch,
) {
    const response = await fetchImpl(`${API_BASE_URL}/api/v1/analyze/detailed`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY,
        },
        body: JSON.stringify({
            message: { sender: "scammer", text, timestamp },
            conversationHistory: toConversationHistory(history),
            metadata: { channel, language: "English", locale },
        }),
    });

    if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
    }
    return parseAnalyzeDetailed(await response.json());
}
