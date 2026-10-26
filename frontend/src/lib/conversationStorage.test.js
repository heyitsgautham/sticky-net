import {
  STORAGE_KEY,
  generateId,
  isSavedConversation,
  loadConversations,
  saveConversations,
} from "./conversationStorage";

const conversation = (id) => ({ id, messages: [{ sender: "scammer", text: "hi" }] });

beforeEach(() => localStorage.clear());

describe("loadConversations", () => {
  it("returns [] when nothing is stored", () => {
    expect(loadConversations()).toEqual([]);
  });

  it("round-trips what saveConversations wrote", () => {
    saveConversations([conversation("a"), conversation("b")]);
    expect(loadConversations().map((c) => c.id)).toEqual(["a", "b"]);
  });

  it.each([
    ["an object", '{"conv-1": {"id": "conv-1"}}'],
    ["a string", '"hello"'],
    ["null", "null"],
    ["broken JSON", "{not json"],
  ])("returns [] when storage holds %s", (_, raw) => {
    localStorage.setItem(STORAGE_KEY, raw);
    expect(loadConversations()).toEqual([]);
  });

  it("drops entries the dashboard cannot render and keeps the rest", () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([conversation("ok"), null, { id: 7, messages: [] }, { id: "no-messages" }]),
    );
    expect(loadConversations().map((c) => c.id)).toEqual(["ok"]);
  });
});

describe("saveConversations", () => {
  it("swallows a storage error such as a full quota", () => {
    const setItem = jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota", "QuotaExceededError");
    });
    expect(() => saveConversations([conversation("a")])).not.toThrow();
    setItem.mockRestore();
  });
});

describe("helpers", () => {
  it("recognises renderable conversations", () => {
    expect(isSavedConversation(conversation("a"))).toBe(true);
    expect(isSavedConversation({ id: "a", messages: "x" })).toBe(false);
    expect(isSavedConversation(undefined)).toBe(false);
  });

  it("generates distinct conv- ids", () => {
    const a = generateId();
    expect(a).toMatch(/^conv-\d+-[a-z0-9]+$/);
    expect(generateId()).not.toBe(a);
  });
});
