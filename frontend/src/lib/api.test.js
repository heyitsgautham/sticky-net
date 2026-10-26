import { analyzeDetailed, checkHealth, toConversationHistory } from "./api";

const okResponse = (body) => ({ ok: true, status: 200, json: async () => body });

describe("analyzeDetailed", () => {
  it("posts the message, history and metadata with the API key", async () => {
    const fetchImpl = jest.fn(async () => okResponse({ status: "success", reply: "hi" }));

    const data = await analyzeDetailed(
      {
        text: "verify now",
        timestamp: "2026-01-21T10:15:30Z",
        history: [{ sender: "scammer", text: "hello", isoTimestamp: "2026-01-21T10:14:00Z" }],
        channel: "WhatsApp",
        locale: "IN",
      },
      fetchImpl,
    );

    expect(data.reply).toBe("hi");
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe("http://localhost:8080/api/v1/analyze/detailed");
    // No REACT_APP_API_KEY in the test environment, so no key header is sent.
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual({
      message: { sender: "scammer", text: "verify now", timestamp: "2026-01-21T10:15:30Z" },
      conversationHistory: [
        { sender: "scammer", text: "hello", timestamp: "2026-01-21T10:14:00Z" },
      ],
      metadata: { channel: "WhatsApp", language: "English", locale: "IN" },
    });
  });

  it("throws on a non-2xx status", async () => {
    const fetchImpl = jest.fn(async () => ({ ok: false, status: 503 }));
    await expect(
      analyzeDetailed(
        { text: "x", timestamp: "t", history: [], channel: "SMS", locale: "IN" },
        fetchImpl,
      ),
    ).rejects.toThrow("API returned 503");
  });
});

describe("checkHealth", () => {
  it("reports the API up or down", async () => {
    expect(await checkHealth(async () => ({ ok: true }))).toBe(true);
    expect(await checkHealth(async () => ({ ok: false }))).toBe(false);
    expect(
      await checkHealth(async () => {
        throw new TypeError("Failed to fetch");
      }),
    ).toBe(false);
  });
});

describe("toConversationHistory", () => {
  it("fills a timestamp for messages saved without one", () => {
    const [entry] = toConversationHistory([{ sender: "agent", text: "ok" }]);
    expect(entry.sender).toBe("agent");
    expect(Number.isNaN(Date.parse(entry.timestamp))).toBe(false);
  });
});

describe("API key header", () => {
  const original = process.env.REACT_APP_API_KEY;
  afterEach(() => {
    if (original === undefined) delete process.env.REACT_APP_API_KEY;
    else process.env.REACT_APP_API_KEY = original;
  });

  it("sends REACT_APP_API_KEY as x-api-key when the build sets it", async () => {
    process.env.REACT_APP_API_KEY = "dashboard-key";
    let api;
    jest.isolateModules(() => {
      api = require("./api");
    });
    const fetchImpl = jest.fn(async () => okResponse({ status: "success", reply: "hi" }));

    await api.analyzeDetailed(
      { text: "x", timestamp: "t", history: [], channel: "SMS", locale: "IN" },
      fetchImpl,
    );

    expect(fetchImpl.mock.calls[0][1].headers["x-api-key"]).toBe("dashboard-key");
  });
});
