import { MAX_HISTORY_MESSAGES, MAX_MESSAGE_CHARS, cleanMessageText } from "./limits";
import { toConversationHistory } from "./api";

const message = (i, text = `message ${i}`) => ({
  sender: i % 2 ? "agent" : "scammer",
  text,
  isoTimestamp: "2026-01-21T10:00:00Z",
});

describe("toConversationHistory limits", () => {
  it("sends only the most recent MAX_HISTORY_MESSAGES entries", () => {
    const messages = Array.from({ length: 102 }, (_, i) => message(i));
    const history = toConversationHistory(messages);

    expect(history).toHaveLength(MAX_HISTORY_MESSAGES);
    expect(history[0].text).toBe("message 2");
    expect(history[history.length - 1].text).toBe("message 101");
  });

  it("keeps a short chat whole", () => {
    expect(toConversationHistory([message(0), message(1)])).toHaveLength(2);
  });

  it("cuts an oversized message to MAX_MESSAGE_CHARS", () => {
    const [entry] = toConversationHistory([message(0, "x".repeat(MAX_MESSAGE_CHARS + 50))]);
    expect(entry.text).toHaveLength(MAX_MESSAGE_CHARS);
  });

  it("treats a saved message without text as empty", () => {
    const [entry] = toConversationHistory([{ sender: "agent" }]);
    expect(entry.text).toBe("");
  });
});

describe("cleanMessageText", () => {
  it("trims and caps the text", () => {
    expect(cleanMessageText("  hi  ")).toBe("hi");
    expect(cleanMessageText("y".repeat(MAX_MESSAGE_CHARS + 1))).toHaveLength(MAX_MESSAGE_CHARS);
  });

  it("returns an empty string for blank input", () => {
    expect(cleanMessageText("   ")).toBe("");
    expect(cleanMessageText(undefined)).toBe("");
  });
});
