import { createLogger } from "./logger";

const fixedNow = () => new Date("2026-01-21T10:15:30Z");

const fakeSink = () => ({ debug: jest.fn(), info: jest.fn(), warn: jest.fn(), error: jest.fn() });

describe("createLogger", () => {
  it("writes one structured entry with the event and context", () => {
    const sink = fakeSink();
    const log = createLogger({ sink, minLevel: "debug", now: fixedNow });

    log.info("conversation saved", { conversationId: "conv-1", messages: 4 });

    expect(sink.info).toHaveBeenCalledWith({
      level: "info",
      event: "conversation saved",
      time: "2026-01-21T10:15:30.000Z",
      conversationId: "conv-1",
      messages: 4,
    });
  });

  it("flattens errors to name and message", () => {
    const sink = fakeSink();
    const log = createLogger({ sink, minLevel: "debug", now: fixedNow });

    const entry = log.error("api request failed", { error: new TypeError("Failed to fetch") });

    expect(entry.error).toEqual({ name: "TypeError", message: "Failed to fetch" });
    expect(JSON.parse(JSON.stringify(entry))).toEqual(entry);
  });

  it("drops entries below the minimum level", () => {
    const sink = fakeSink();
    const log = createLogger({ sink, minLevel: "warn" });

    expect(log.info("ignored")).toBeNull();
    log.warn("kept");

    expect(sink.info).not.toHaveBeenCalled();
    expect(sink.warn).toHaveBeenCalledTimes(1);
  });

  it("silent writes nothing at all", () => {
    const sink = fakeSink();
    createLogger({ sink, minLevel: "silent" }).error("ignored");
    expect(sink.error).not.toHaveBeenCalled();
  });

  it("falls back to log when the sink lacks a level method", () => {
    const sink = { log: jest.fn() };
    createLogger({ sink, minLevel: "debug" }).warn("fallback");
    expect(sink.log).toHaveBeenCalledWith(expect.objectContaining({ level: "warn", event: "fallback" }));
  });

  it("is silent by default under jest", () => {
    const sink = fakeSink();
    createLogger({ sink }).error("ignored in tests");
    expect(sink.error).not.toHaveBeenCalled();
  });
});
