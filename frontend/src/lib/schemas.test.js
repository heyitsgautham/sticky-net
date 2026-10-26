import { ApiResponseError, parseAnalyzeDetailed } from "./schemas";
import { analyzeDetailed } from "./api";

// Shaped like a real /api/v1/analyze/detailed reply for a scam turn.
const detailed = {
  status: "success",
  scamDetected: true,
  scamType: "banking_fraud",
  confidence: 0.92,
  engagementMetrics: { engagementDurationSeconds: 25, totalMessagesExchanged: 2 },
  extractedIntelligence: {
    bankAccounts: [],
    upiIds: ["fraud.help@okaxis"],
    phoneNumbers: ["+919876543210"],
    phishingLinks: [],
    emailAddresses: [],
    beneficiaryNames: [],
    bankNames: [],
    ifscCodes: [],
    whatsappNumbers: [],
    suspiciousKeywords: [],
    caseIds: [],
    policyNumbers: [],
    orderNumbers: [],
  },
  agentNotes: "Mode: aggressive",
  agentResponse: "which account sir?",
};

describe("parseAnalyzeDetailed", () => {
  it("accepts a full detailed response", () => {
    expect(parseAnalyzeDetailed(detailed)).toEqual(detailed);
  });

  it("accepts the two-key fallback the API sends for a body it cannot parse", () => {
    const fallback = { status: "success", reply: "sorry i didnt understand that... can you say again?" };
    expect(parseAnalyzeDetailed(fallback)).toEqual(fallback);
  });

  it("accepts a harmless verdict with no scam type", () => {
    expect(parseAnalyzeDetailed({ ...detailed, scamDetected: false, scamType: null }).scamType).toBeNull();
  });

  it("keeps fields it does not know about", () => {
    expect(parseAnalyzeDetailed({ ...detailed, newField: 1 }).newField).toBe(1);
  });

  it.each([
    ["a missing status", { reply: "hi" }],
    ["an unknown status", { ...detailed, status: "ok" }],
    ["intel that is not a list", { ...detailed, extractedIntelligence: { upiIds: "a@okaxis" } }],
    ["confidence above 1", { ...detailed, confidence: 92 }],
    ["an HTML error page", "<html>Bad Gateway</html>"],
  ])("rejects %s", (_, body) => {
    expect(() => parseAnalyzeDetailed(body)).toThrow(ApiResponseError);
  });

  it("lists zod's issues on the error", () => {
    try {
      parseAnalyzeDetailed({ ...detailed, confidence: "high" });
    } catch (error) {
      expect(error.issues[0].path).toEqual(["confidence"]);
    }
    expect.assertions(1);
  });
});

describe("analyzeDetailed validation", () => {
  const args = { text: "x", timestamp: "t", history: [], channel: "SMS", locale: "IN" };

  it("returns the validated body", async () => {
    const fetchImpl = jest.fn(async () => ({ ok: true, status: 200, json: async () => detailed }));
    await expect(analyzeDetailed(args, fetchImpl)).resolves.toEqual(detailed);
  });

  it("throws when a 200 carries the wrong shape", async () => {
    const fetchImpl = jest.fn(async () => ({ ok: true, status: 200, json: async () => ({ ok: 1 }) }));
    await expect(analyzeDetailed(args, fetchImpl)).rejects.toThrow("API returned an unexpected response");
  });
});
