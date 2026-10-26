// Structured client-side logging for the dashboard.
//
// Every entry is one object: { level, event, time, ...context }. Errors in the
// context are flattened to name and message, so entries stay plain JSON that a
// browser log collector can ship as is. Below minLevel, nothing is written.

export const LEVELS = { debug: 10, info: 20, warn: 30, error: 40, silent: 100 };

const defaultLevel = () => {
  if (process.env.NODE_ENV === "test") return "silent";
  return process.env.NODE_ENV === "production" ? "warn" : "debug";
};

const serialise = (value) =>
  value instanceof Error ? { name: value.name, message: value.message } : value;

export function createLogger({
  sink = console,
  minLevel = defaultLevel(),
  now = () => new Date(),
} = {}) {
  const threshold = LEVELS[minLevel] ?? LEVELS.debug;

  const write =
    (level) =>
    (event, context = {}) => {
      if (LEVELS[level] < threshold) return null;
      const entry = { level, event, time: now().toISOString() };
      for (const [key, value] of Object.entries(context)) {
        entry[key] = serialise(value);
      }
      const method = typeof sink[level] === "function" ? sink[level] : sink.log;
      method.call(sink, entry);
      return entry;
    };

  return {
    debug: write("debug"),
    info: write("info"),
    warn: write("warn"),
    error: write("error"),
  };
}

export const logger = createLogger();
