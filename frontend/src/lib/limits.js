// Request limits the API enforces in src/api/schemas.py. A request over either
// limit gets the evaluator-safe "say again" reply instead of an analysis.
export const MAX_MESSAGE_CHARS = 10000;
export const MAX_HISTORY_MESSAGES = 100;

// The text to send for one message: trimmed, and empty when there is nothing to send.
export const cleanMessageText = (text) => (text || "").trim().slice(0, MAX_MESSAGE_CHARS);
