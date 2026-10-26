import { fireEvent, render, screen } from "@testing-library/react";
import { ChatMessage, ConversationCard, IntelTag, MetricCard } from "@/components/chat/ChatWidgets";

describe("ChatMessage", () => {
  it("renders the text and aligns agent replies to the right", () => {
    const { container, rerender } = render(
      <ChatMessage message={{ text: "which account?" }} isAgent />,
    );
    expect(screen.getByText("which account?")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("justify-end");

    rerender(<ChatMessage message={{ text: "pay now" }} isAgent={false} />);
    expect(container.firstChild).toHaveClass("justify-start");
  });
});

describe("MetricCard", () => {
  it("shows the label and value", () => {
    render(<MetricCard label="Confidence" value="92%" color="red" />);
    expect(screen.getByText("Confidence")).toBeInTheDocument();
    expect(screen.getByText("92%")).toHaveClass("text-cyber-red");
  });
});

describe("IntelTag", () => {
  it.each([
    ["upi", "UPI ID:"],
    ["phone", "Phone:"],
    ["bank", "Bank A/C:"],
    ["email", "Email:"],
    ["link", "Link:"],
    ["other", "Other:"],
  ])("labels a %s find", (type, label) => {
    render(<IntelTag type={type} value="x" />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("falls back to the UPI style for an unknown type", () => {
    render(<IntelTag type="mystery" value="x" />);
    expect(screen.getByText("UPI ID:")).toBeInTheDocument();
  });

  it("copies the value to the clipboard", () => {
    const writeText = jest.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    render(<IntelTag type="upi" value="fraud@okaxis" />);

    fireEvent.click(screen.getByRole("button", { name: "Copy UPI ID fraud@okaxis" }));

    expect(writeText).toHaveBeenCalledWith("fraud@okaxis");
  });
});

describe("ConversationCard", () => {
  const saved = {
    id: "conv-1",
    title: "SBI blocked...",
    preview: "Your SBI account",
    messages: [{}, {}, {}],
    metrics: { confidence: 0.92 },
  };

  it("shows the title, preview, confidence and message count", () => {
    render(<ConversationCard conversation={saved} onClick={jest.fn()} />);
    expect(screen.getByText("SBI blocked...")).toBeInTheDocument();
    expect(screen.getByText("Your SBI account")).toBeInTheDocument();
    expect(screen.getByText("92% conf")).toBeInTheDocument();
    expect(screen.getByText("3 msgs")).toBeInTheDocument();
  });

  it("selects on click and deletes without selecting", () => {
    const onClick = jest.fn();
    const onDelete = jest.fn();
    render(<ConversationCard conversation={saved} onClick={onClick} onDelete={onDelete} />);

    const select = screen.getByRole("button", { name: /^SBI blocked/ });
    fireEvent.click(screen.getByRole("button", { name: "Delete conversation SBI blocked..." }));
    expect(onDelete).toHaveBeenCalledWith("conv-1");
    expect(onClick).not.toHaveBeenCalled();

    fireEvent.click(select);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("offers no delete button for a sample", () => {
    render(
      <ConversationCard
        conversation={{ ...saved, isSample: true }}
        onClick={jest.fn()}
        onDelete={jest.fn()}
      />,
    );
    expect(screen.getAllByRole("button")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /Delete conversation/ })).not.toBeInTheDocument();
  });
});
