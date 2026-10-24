import { emptyIntel, extractionOrderFrom, hasAnyIntel, mergeIntel } from "./intel";

describe("mergeIntel", () => {
  it("adds new items and reports them in feed order", () => {
    const { updated, newExtractions } = mergeIntel(emptyIntel(), {
      upiIds: ["fraud@ybl"],
      bankAccounts: ["123456789012"],
    });

    expect(updated.upiIds).toEqual(["fraud@ybl"]);
    expect(updated.bankAccounts).toEqual(["123456789012"]);
    expect(newExtractions).toEqual([
      { type: "bank", value: "123456789012" },
      { type: "upi", value: "fraud@ybl" },
    ]);
  });

  it("reads emails from the API's emailAddresses field", () => {
    const { updated, newExtractions } = mergeIntel(emptyIntel(), {
      emailAddresses: ["help@sbi-verify.com"],
    });

    expect(updated.emails).toEqual(["help@sbi-verify.com"]);
    expect(newExtractions).toEqual([{ type: "email", value: "help@sbi-verify.com" }]);
  });

  it("skips items the conversation already has", () => {
    const prev = { ...emptyIntel(), phoneNumbers: ["9876543210"] };

    const { updated, newExtractions } = mergeIntel(prev, {
      phoneNumbers: ["9876543210", "9123456780"],
    });

    expect(updated.phoneNumbers).toEqual(["9876543210", "9123456780"]);
    expect(newExtractions).toEqual([{ type: "phone", value: "9123456780" }]);
  });

  it("does not mutate the previous state", () => {
    const prev = emptyIntel();
    mergeIntel(prev, { upiIds: ["a@ybl"] });
    expect(prev.upiIds).toEqual([]);
  });

  it("fills fields missing from older saved conversations", () => {
    const legacy = { upiIds: ["a@ybl"] };
    const { updated } = mergeIntel(legacy, {});
    expect(updated.bankNames).toEqual([]);
    expect(updated.upiIds).toEqual(["a@ybl"]);
  });

  it("lists other_critical_info once with its label", () => {
    const { newExtractions } = mergeIntel(emptyIntel(), {
      other_critical_info: [
        { label: "Case ID", value: "REF-1" },
        { label: "Case ID", value: "REF-1" },
      ],
    });
    expect(newExtractions).toEqual([{ type: "other", value: "Case ID: REF-1" }]);
  });
});

describe("extractionOrderFrom", () => {
  it("rebuilds the feed from stored intel", () => {
    const intel = { ...emptyIntel(), emails: ["x@fake.com"], ifscCodes: ["SBIN0001234"] };
    expect(extractionOrderFrom(intel)).toEqual([
      { type: "ifsc", value: "SBIN0001234" },
      { type: "email", value: "x@fake.com" },
    ]);
  });
});

describe("hasAnyIntel", () => {
  it("is false for an empty conversation and true once anything lands", () => {
    expect(hasAnyIntel(emptyIntel())).toBe(false);
    expect(hasAnyIntel({ ...emptyIntel(), bankNames: ["SBI"] })).toBe(true);
  });
});
