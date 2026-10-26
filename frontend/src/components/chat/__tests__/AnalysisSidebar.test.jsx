import { fireEvent, render, screen } from "@testing-library/react";
import { AnalysisSidebar } from "@/components/chat/AnalysisSidebar";

const props = (overrides = {}) => ({
  channel: "SMS",
  setChannel: jest.fn(),
  locale: "IN",
  setLocale: jest.fn(),
  metrics: { scamDetected: null, confidence: null, messagesExchanged: 0 },
  extractionOrder: [],
  agentNotes: "",
  ...overrides,
});

describe("AnalysisSidebar", () => {
  it("shows placeholders before the first analysis", () => {
    render(<AnalysisSidebar {...props()} />);
    expect(screen.getAllByText("-")).toHaveLength(3); // verdict, confidence, notes
    expect(screen.getByText("No intelligence extracted yet.")).toBeInTheDocument();
  });

  it("shows the verdict, confidence, count, finds and notes", () => {
    render(
      <AnalysisSidebar
        {...props({
          metrics: { scamDetected: true, confidence: 0.92, messagesExchanged: 4 },
          extractionOrder: [
            { type: "upi", value: "fraud@okaxis" },
            { type: "phone", value: "+919876543210" },
          ],
          agentNotes: "Mode: aggressive",
        })}
      />,
    );
    expect(screen.getByText("YES")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("fraud@okaxis")).toBeInTheDocument();
    expect(screen.getByText("+919876543210")).toBeInTheDocument();
    expect(screen.getByText("Mode: aggressive")).toBeInTheDocument();
  });

  it("says NO for a harmless verdict", () => {
    render(
      <AnalysisSidebar
        {...props({ metrics: { scamDetected: false, confidence: 0.1, messagesExchanged: 2 } })}
      />,
    );
    expect(screen.getByText("NO")).toBeInTheDocument();
    expect(screen.getByText("10%")).toBeInTheDocument();
  });

  it("reports channel and locale changes", () => {
    const p = props();
    render(<AnalysisSidebar {...p} />);
    fireEvent.change(screen.getByLabelText("CHANNEL"), { target: { value: "WhatsApp" } });
    fireEvent.change(screen.getByLabelText("LOCALE"), { target: { value: "UK" } });
    expect(p.setChannel).toHaveBeenCalledWith("WhatsApp");
    expect(p.setLocale).toHaveBeenCalledWith("UK");
  });
});
