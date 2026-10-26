// Extracted-intelligence bookkeeping for the chat dashboard.
//
// Dashboard state keeps emails under `emails`, while the API's
// ExtractedIntelligence model sends them as `emailAddresses`.

// Field name in dashboard state, and the tag type IntelTag renders for it.
// The order is the order new finds appear in the extraction feed.
export const INTEL_FIELDS = [
  ["bankAccounts", "bank"],
  ["ifscCodes", "ifsc"],
  ["bankNames", "bankName"],
  ["beneficiaryNames", "name"],
  ["upiIds", "upi"],
  ["phoneNumbers", "phone"],
  ["whatsappNumbers", "whatsapp"],
  ["phishingLinks", "link"],
  ["emails", "email"],
];

export const emptyIntel = () => Object.fromEntries(INTEL_FIELDS.map(([field]) => [field, []]));

const incomingValues = (intel, field) =>
  field === "emails"
    ? [...(intel.emailAddresses || []), ...(intel.emails || [])]
    : intel[field] || [];

// Add an API response's intelligence to what the conversation already holds.
// Returns the merged state and the new items, in feed order.
export function mergeIntel(prev, intel) {
  const updated = emptyIntel();
  const newExtractions = [];

  for (const [field, type] of INTEL_FIELDS) {
    updated[field] = [...(prev?.[field] || [])];
    for (const item of incomingValues(intel, field)) {
      if (!updated[field].includes(item)) {
        updated[field].push(item);
        newExtractions.push({ type, value: item });
      }
    }
  }

  // other_critical_info items carry their own label and only feed the list.
  for (const item of intel.other_critical_info || []) {
    const value = `${item.label}: ${item.value}`;
    if (!newExtractions.some((e) => e.type === "other" && e.value === value)) {
      newExtractions.push({ type: "other", value });
    }
  }

  return { updated, newExtractions };
}

// Rebuild the extraction feed for a saved conversation that has none stored.
export function extractionOrderFrom(intel) {
  return INTEL_FIELDS.flatMap(([field, type]) =>
    (intel[field] || []).map((value) => ({ type, value })),
  );
}
