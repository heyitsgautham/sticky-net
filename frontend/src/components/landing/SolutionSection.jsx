// How the honeypot works, shown as a chat mock and terminal analysis.
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Terminal, Smartphone } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { fadeInUp, fadeInScale } from "@/components/landing/motion";

// ============ SOLUTION SECTION (Split Screen) ============
export const WhatsAppMock = () => {
  const messages = [
    {
      type: "incoming",
      text: "Dear Customer, Your SBI account will be BLOCKED within 24 hours due to incomplete KYC verification. Update immediately to avoid account suspension.",
      time: "10:31 AM",
    },
    {
      type: "outgoing",
      text: "oh god sir pls dont block my account. my pension comes in sbi only. i am old lady i dont understand what is kyc. what i have to do? pls tell me",
      time: "10:32 AM",
    },
    {
      type: "incoming",
      text: "This is urgent matter. I am calling from SBI head office Mumbai. Your account ending 4521 is showing KYC pending.",
      time: "10:33 AM",
    },
    {
      type: "outgoing",
      text: "hello beta i am very worried. i cannot come to mumbai i live in pune. my knees are bad i cannot walk much. how can i do this verification from home?",
      time: "10:34 AM",
    },
    {
      type: "incoming",
      text: "Please share your registered mobile number. Or you can directly update by paying Rs.10 verification fee to UPI ID: sbi.kyc.update@ybl",
      time: "10:35 AM",
    },
    {
      type: "outgoing",
      text: "ok beta i will pay 10 rs right now. i am opening my phone pay app... what name should show on screen? i want to be sure it is going to bank only.",
      time: "10:37 AM",
    },
  ];

  return (
    <div
      className="bg-[#0B141A] rounded-xl overflow-hidden border border-white/10 max-w-sm mx-auto"
      data-testid="whatsapp-mock"
    >
      {/* Header */}
      <div className="bg-[#1F2C34] px-4 py-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-cyber-cyan/30 to-cyber-cyan/10 flex items-center justify-center">
          <span className="text-lg">👵</span>
        </div>
        <div>
          <div className="text-white font-medium text-sm">Pushpa Verma</div>
          <div className="text-gray-500 text-xs">online</div>
        </div>
      </div>

      {/* Messages */}
      <div className="p-4 space-y-3 h-80 overflow-y-auto">
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.3 }}
            className={`flex ${msg.type === "outgoing" ? "justify-end" : "justify-start"}`}
          >
            <div className={`whatsapp-bubble ${msg.type}`}>
              <p>{msg.text}</p>
              <span className="text-[10px] text-gray-500 mt-1 block text-right">{msg.time}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const TerminalAnalysis = () => {
  const logs = [
    { type: "system", text: "[DETECT] Incoming message analyzed..." },
    { type: "ai", text: "> SCAM_PROBABILITY: 100.0%" },
    { type: "ai", text: "> SCAM_TYPE: banking_fraud" },
    { type: "ai", text: "> CONFIDENCE: AGGRESSIVE (1.0)" },
    { type: "system", text: "[ENGAGE] Mode: aggressive | Turn: 1" },
    { type: "ai", text: "> DEPLOYING_PERSONA: panicked_elderly" },
    { type: "system", text: "[INTEL] Turn 3: UPI extraction..." },
    { type: "extract", text: "> ✓ UPI_CAPTURED: sbi.kyc.update@ybl" },
    { type: "ai", text: "> TACTIC: verification_stalling" },
    { type: "system", text: "[STATUS] Duration: 6m 12s | Intel: 1 UPI" },
    { type: "system", text: "[SUCCESS] Scammer time wasted ✓" },
  ];

  return (
    <div className="terminal-window max-w-md mx-auto" data-testid="terminal-analysis">
      <div className="terminal-header">
        <div className="terminal-dot red" />
        <div className="terminal-dot yellow" />
        <div className="terminal-dot green" />
        <span className="text-gray-500 text-sm ml-2 font-mono">sticky-net.exe</span>
      </div>
      <div className="terminal-body">
        {logs.map((log, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.4 }}
            className={`mb-2 ${
              log.type === "ai"
                ? "text-cyber-cyan"
                : log.type === "extract"
                  ? "text-yellow-400"
                  : "text-gray-500"
            }`}
          >
            {log.text}
          </motion.div>
        ))}
        <span className="text-cyber-cyan cursor-blink">█</span>
      </div>
    </div>
  );
};

export const SolutionSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, amount: 0.5 });

  return (
    <section
      id="solution"
      className="snap-section px-6 grid-bg flex items-center"
      data-testid="solution-section"
    >
      <div ref={ref} className="max-w-7xl mx-auto w-full">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-12"
        >
          <Badge
            className="mb-4 border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10 font-mono"
            data-testid="solution-badge"
          >
            THE SOLUTION
          </Badge>
          <h2 className="font-heading text-3xl md:text-5xl font-bold text-white mb-4">
            One Persona, Two Realities
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            What the scammer sees vs. what&apos;s really happening behind the scenes.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 md:gap-8 items-start">
          <motion.div
            variants={fadeInScale}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
          >
            <div className="flex items-center gap-2 mb-4">
              <Smartphone className="w-5 h-5 text-green-500" />
              <span className="text-sm text-gray-400 font-mono uppercase">What Scammer Sees</span>
            </div>
            <WhatsAppMock />
          </motion.div>

          <motion.div
            variants={fadeInScale}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            transition={{ delay: 0.2 }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="w-5 h-5 text-cyber-cyan" />
              <span className="text-sm text-gray-400 font-mono uppercase">
                What&apos;s Really Happening
              </span>
            </div>
            <TerminalAnalysis />
          </motion.div>
        </div>
      </div>
    </section>
  );
};
