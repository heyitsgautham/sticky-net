import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ChatDashboard from "@/components/ChatDashboard";
import { STORAGE_KEY } from "@/lib/conversationStorage";

const detailed = {
  status: "success",
  scamDetected: true,
  scamType: "banking_fraud",
  confidence: 0.92,
  engagementMetrics: { engagementDurationSeconds: 25, totalMessagesExchanged: 2 },
  extractedIntelligence: { upiIds: ["fraud.help@okaxis"], phoneNumbers: [], emailAddresses: [] },
  agentNotes: "Mode: aggressive | Type: banking_fraud",
  agentResponse: "oh no which account sir?",
};

const respond = (body, ok = true) => ({ ok, status: ok ? 200 : 503, json: async () => body });

function mockApi(analyze) {
  global.fetch = jest.fn(async (url) =>
    String(url).endsWith("/health") ? respond({ status: "healthy" }) : analyze(url),
  );
}

// Renders the dashboard and waits for its mount-time health check to settle.
async function renderDashboard() {
  const view = render(
    <MemoryRouter>
      <ChatDashboard />
    </MemoryRouter>,
  );
  await screen.findByText("API Connected");
  return view;
}

const send = (text) => {
  fireEvent.change(screen.getByPlaceholderText(/Type scammer message/), { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: /Send/ }));
};

beforeEach(() => localStorage.clear());
afterEach(() => delete global.fetch);

describe("ChatDashboard", () => {
  it("shows the agent reply, verdict and intel for a scam message", async () => {
    mockApi(async () => respond(detailed));
    await renderDashboard();

    send("Your SBI account is blocked. Pay to fraud.help@okaxis");

    expect(await screen.findByText("oh no which account sir?")).toBeInTheDocument();
    expect(screen.getByText("Your SBI account is blocked. Pay to fraud.help@okaxis")).toBeInTheDocument();
    expect(screen.getByText("YES")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("fraud.help@okaxis")).toBeInTheDocument();
    expect(screen.getByText(/Mode: aggressive/)).toBeInTheDocument();

    // The dashboard saves in an effect after the reply renders.
    await waitFor(() => {
      const [saved] = JSON.parse(localStorage.getItem(STORAGE_KEY));
      expect(saved.messages.map((m) => m.sender)).toEqual(["scammer", "agent"]);
    });
  });

  it("sends the message, history and metadata to the detailed endpoint", async () => {
    mockApi(async () => respond(detailed));
    await renderDashboard();

    send("first");
    await screen.findByText("oh no which account sir?");
    send("second");
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));

    const [, init] = global.fetch.mock.calls[2];
    const body = JSON.parse(init.body);
    expect(body.message.text).toBe("second");
    expect(body.conversationHistory.map((m) => m.text)).toEqual(["first", "oh no which account sir?"]);
    expect(body.metadata).toEqual({ channel: "SMS", language: "English", locale: "IN" });
  });

  it("marks the API offline and explains when the request fails", async () => {
    mockApi(async () => respond({}, false));
    await renderDashboard();

    send("hello");

    expect(await screen.findByText("API Offline")).toBeInTheDocument();
    expect(screen.getByText(/Connection error: API returned 503/)).toBeInTheDocument();
  });

  it("treats a malformed 200 response as an error instead of rendering it", async () => {
    mockApi(async () => respond({ unexpected: true }));
    await renderDashboard();

    send("hello");

    expect(await screen.findByText(/API returned an unexpected response/)).toBeInTheDocument();
  });

  it("ignores blank input", async () => {
    mockApi(async () => respond(detailed));
    await renderDashboard();

    send("   ");

    expect(screen.getByRole("button", { name: /Send/ })).toBeDisabled();
    expect(global.fetch).toHaveBeenCalledTimes(1); // only the health check
  });

  it("opens a saved conversation and deletes it", async () => {
    const saved = {
      id: "conv-saved",
      // The dashboard rewrites the title from the first message whenever it saves.
      title: "earlier scam...",
      preview: "earlier",
      messages: [
        { sender: "scammer", text: "earlier scam", isoTimestamp: "2026-01-21T10:00:00Z" },
        { sender: "agent", text: "earlier reply", isoTimestamp: "2026-01-21T10:00:01Z" },
      ],
      extractedIntel: { upiIds: ["saved@okaxis"] },
      metrics: { scamDetected: true, confidence: 0.7, messagesExchanged: 2 },
      agentNotes: "saved notes",
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify([saved]));
    mockApi(async () => respond(detailed));
    await renderDashboard();

    fireEvent.click(screen.getByText("earlier scam..."));
    expect(screen.getByText("earlier reply")).toBeInTheDocument();
    // The extraction feed is rebuilt from the saved intel.
    expect(screen.getByText("saved@okaxis")).toBeInTheDocument();
    expect(screen.getByText("saved notes")).toBeInTheDocument();

    const card = screen.getByText("earlier scam...").closest("div.group");
    const [, remove] = card.querySelectorAll("button");
    fireEvent.click(remove);

    expect(screen.queryByText("earlier scam...")).not.toBeInTheDocument();
    expect(screen.queryByText("earlier reply")).not.toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY))).toEqual([]);
  });

  it("clears the chat on Reset", async () => {
    mockApi(async () => respond(detailed));
    await renderDashboard();
    send("hello");
    await screen.findByText("oh no which account sir?");

    fireEvent.click(screen.getByRole("button", { name: /Reset/ }));

    expect(screen.queryByText("oh no which account sir?")).not.toBeInTheDocument();
    expect(screen.getByText(/Start a conversation/)).toBeInTheDocument();
  });

  it("opens a sample conversation read-only", async () => {
    mockApi(async () => respond(detailed));
    await renderDashboard();

    fireEvent.click(screen.getAllByText(/Bank Fraud/)[0]);

    expect(screen.getByText("DEMO - READ ONLY")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/Type scammer message/)).not.toBeInTheDocument();
  });
});
