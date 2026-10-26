// Runtime checks for what the API sends back, built with zod.
//
// /api/v1/analyze/detailed answers with AnalyzeResponse from src/api/schemas.py,
// or, for a body the API could not parse, with only { status, reply }. Both pass.
// Anything else, such as an HTML error page from a proxy or a field of the wrong
// type, fails here instead of crashing a component that reads it.
import { z } from "zod";

const stringList = z.array(z.string());

export const ExtractedIntelligenceSchema = z
  .object({
    bankAccounts: stringList.optional(),
    upiIds: stringList.optional(),
    phoneNumbers: stringList.optional(),
    phishingLinks: stringList.optional(),
    emailAddresses: stringList.optional(),
    beneficiaryNames: stringList.optional(),
    bankNames: stringList.optional(),
    ifscCodes: stringList.optional(),
    whatsappNumbers: stringList.optional(),
    suspiciousKeywords: stringList.optional(),
    caseIds: stringList.optional(),
    policyNumbers: stringList.optional(),
    orderNumbers: stringList.optional(),
  })
  .passthrough();

export const AnalyzeDetailedResponseSchema = z
  .object({
    status: z.enum(["success", "error"]),
    reply: z.string().optional(),
    scamDetected: z.boolean().optional(),
    scamType: z.string().nullable().optional(),
    confidence: z.number().min(0).max(1).optional(),
    engagementMetrics: z
      .object({
        engagementDurationSeconds: z.number().int().nonnegative(),
        totalMessagesExchanged: z.number().int().nonnegative(),
      })
      .partial()
      .optional(),
    extractedIntelligence: ExtractedIntelligenceSchema.optional(),
    agentNotes: z.string().optional(),
    agentResponse: z.string().nullable().optional(),
  })
  .passthrough();

export class ApiResponseError extends Error {
  constructor(issues) {
    super("API returned an unexpected response");
    this.name = "ApiResponseError";
    this.issues = issues;
  }
}

// Parse a detailed-endpoint body, throwing ApiResponseError with zod's issues on a mismatch.
export function parseAnalyzeDetailed(body) {
  const result = AnalyzeDetailedResponseSchema.safeParse(body);
  if (!result.success) {
    throw new ApiResponseError(result.error.issues);
  }
  return result.data;
}
