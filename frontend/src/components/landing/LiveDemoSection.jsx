// Scripted terminal replay of a honeypot conversation, with a link to the live chat.
import { useEffect, useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import { Bug, Terminal, Github, Play, Pause, Circle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { fadeInUp, fadeInScale } from "@/components/landing/motion";

// ============ LIVE DEMO (Terminal) ============
export const demoConversation = [
  { speaker: "system", text: "━━━ SESSION #4821 STARTED ━━━", delay: 0 },
  { speaker: "system", text: "Target: +91-98XXX-XX412", delay: 500 },
  { speaker: "system", text: "Persona Active: PUSHPA_VERMA (grandmother)", delay: 800 },
  { speaker: "system", text: "", delay: 1000 },
  { speaker: "scammer", text: "[SCAMMER]: Hello madam, I am calling from SBI bank", delay: 1500 },
  {
    speaker: "scammer",
    text: "[SCAMMER]: Your account will be blocked. Share OTP to verify.",
    delay: 2500,
  },
  {
    speaker: "system",
    text: "> THREAT_ANALYSIS: Bank impersonation detected (97.2%)",
    delay: 3500,
  },
  { speaker: "system", text: "> STRATEGY: Express confusion, request clarification", delay: 4000 },
  {
    speaker: "ai",
    text: "[PUSHPA]: Arrey beta, which SBI? I have account in Punjab National Bank...",
    delay: 4500,
  },
  {
    speaker: "scammer",
    text: "[SCAMMER]: Madam this is central office. All banks connected.",
    delay: 5500,
  },
  {
    speaker: "ai",
    text: "[PUSHPA]: Oh achha? My husband used to handle all this. He is no more 😢",
    delay: 6500,
  },
  {
    speaker: "system",
    text: "> TACTIC: Emotional delay deployed (+45 seconds gained)",
    delay: 7500,
  },
  {
    speaker: "scammer",
    text: "[SCAMMER]: Sorry madam. But urgent. OTP please or money gone.",
    delay: 8500,
  },
  { speaker: "ai", text: "[PUSHPA]: Beta wait, my phone is showing many numbers...", delay: 9500 },
  {
    speaker: "ai",
    text: "[PUSHPA]: One says 847291, one says 552183... which one you need?",
    delay: 10500,
  },
  { speaker: "system", text: "> BAIT_DEPLOYED: Fake OTP sequence", delay: 11500 },
  { speaker: "system", text: "> EXTRACTING: Voice pattern analysis...", delay: 12000 },
  { speaker: "scammer", text: "[SCAMMER]: 847291 madam! Quick quick!", delay: 12500 },
  { speaker: "system", text: "> BEHAVIOR_LOGGED: High urgency tactics", delay: 13500 },
  {
    speaker: "ai",
    text: "[PUSHPA]: Oh wait beta, my daughter is calling on other phone...",
    delay: 14000,
  },
  { speaker: "ai", text: "[PUSHPA]: Can I call you back? What is your number?", delay: 14800 },
  { speaker: "system", text: "> INTEL_ATTEMPT: Phone number extraction initiated", delay: 15500 },
  { speaker: "scammer", text: "[SCAMMER]: No madam no callback. Just tell OTP now.", delay: 16500 },
  { speaker: "system", text: "> SCAM_INDICATOR: Callback refusal logged", delay: 17500 },
  {
    speaker: "ai",
    text: "[PUSHPA]: Beta, at least tell UPI ID. I will send ₹1 to verify you are real bank.",
    delay: 18500,
  },
  { speaker: "scammer", text: "[SCAMMER]: OK madam. UPI is bank.verify@ybl", delay: 19500 },
  { speaker: "system", text: "> ✓ UPI_EXTRACTED: bank.verify@ybl", delay: 20500 },
  { speaker: "system", text: "> ✓ FLAGGED: Suspicious UPI pattern detected", delay: 21000 },
  { speaker: "system", text: "", delay: 21500 },
  { speaker: "system", text: "━━━ SESSION SUMMARY ━━━", delay: 22000 },
  { speaker: "system", text: "Duration: 8 minutes 23 seconds", delay: 22500 },
  {
    speaker: "system",
    text: "Intel Captured: Phone, UPI ID, Voice Pattern, Tactics",
    delay: 23000,
  },
  { speaker: "system", text: "Status: SCAMMER WASTED ✓", delay: 23500 },
];

export const LiveTerminal = () => {
  const terminalRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!isPlaying || currentIndex >= demoConversation.length) return;

    const currentLog = demoConversation[currentIndex];
    const delay =
      currentIndex === 0
        ? 500
        : currentLog.delay - (demoConversation[currentIndex - 1]?.delay || 0);

    const timer = setTimeout(() => {
      setLogs((prev) => [...prev, currentLog]);
      setCurrentIndex((prev) => prev + 1);
    }, delay);

    return () => clearTimeout(timer);
  }, [isPlaying, currentIndex]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const handlePlayPause = () => {
    if (currentIndex >= demoConversation.length) {
      // Reset
      setLogs([]);
      setCurrentIndex(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handleRestart = () => {
    setLogs([]);
    setCurrentIndex(0);
    setIsPlaying(true);
  };

  const getSpeakerColor = (speaker) => {
    switch (speaker) {
      case "scammer":
        return "text-cyber-red";
      case "ai":
        return "text-cyber-cyan";
      case "system":
        return "text-gray-500";
      default:
        return "text-gray-400";
    }
  };

  const progress = (currentIndex / demoConversation.length) * 100;
  const isComplete = currentIndex >= demoConversation.length;

  return (
    <div className="terminal-window w-full max-w-4xl mx-auto" data-testid="live-terminal">
      {/* Terminal Header */}
      <div className="terminal-header justify-between">
        <div className="flex items-center">
          <div className="terminal-dot red" />
          <div className="terminal-dot yellow" />
          <div className="terminal-dot green" />
          <span className="text-gray-500 text-sm ml-4 font-mono">sticky-net-demo.log</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Live Indicator */}
          <div className="flex items-center gap-2">
            <Circle
              className={`w-2 h-2 ${isPlaying ? "text-green-500" : "text-gray-500"}`}
              fill="currentColor"
            />
            <span className={`text-xs font-mono ${isPlaying ? "text-green-500" : "text-gray-500"}`}>
              {isPlaying ? "LIVE" : isComplete ? "COMPLETE" : "PAUSED"}
            </span>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleRestart}
              className="h-8 px-3 text-gray-400 hover:text-white"
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Restart
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handlePlayPause}
              className={`h-8 px-3 ${isPlaying ? "text-yellow-500 hover:text-yellow-400" : "text-green-500 hover:text-green-400"}`}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4 mr-1" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1" />
                  {isComplete ? "Replay" : "Play"}
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div ref={terminalRef} className="terminal-body h-96 overflow-y-auto scroll-smooth">
        {logs.length === 0 && !isPlaying ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <Terminal className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="font-mono text-sm">Press Play to start the demo</p>
            </div>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
            {logs.map((log, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={`mb-1 ${getSpeakerColor(log.speaker)} ${log.text === "" ? "h-4" : ""}`}
              >
                {log.text}
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        {isPlaying && currentIndex < demoConversation.length && (
          <span className="inline-block w-2 h-4 bg-cyber-cyan cursor-blink ml-1" />
        )}
      </div>

      {/* Progress Bar */}
      <div className="h-1 bg-gray-800">
        <motion.div
          className="h-full bg-gradient-to-r from-cyber-cyan to-green-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </div>
  );
};

export const LiveDemoSection = ({ onLiveDemo }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, amount: 0.3 });

  return (
    <section
      id="live-demo"
      className="snap-section px-6 grid-bg flex flex-col"
      data-testid="live-demo-section"
    >
      <div ref={ref} className="max-w-7xl mx-auto w-full flex-1 flex flex-col justify-center py-16">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-8"
        >
          <Badge
            className="mb-4 border-green-500 text-green-500 bg-green-500/10 font-mono"
            data-testid="live-demo-badge"
          >
            LIVE DEMO
          </Badge>
          <h2 className="font-heading text-3xl md:text-5xl font-bold text-white mb-4">
            Watch the Trap in Action
          </h2>
          <p className="text-gray-400 max-w-2xl mx-auto">
            Real-time feed of scammers being engaged, delayed, and documented.
          </p>
        </motion.div>

        <motion.div
          variants={fadeInScale}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="flex-1 max-h-[60vh]"
        >
          <LiveTerminal />
        </motion.div>

        {/* Try It Yourself Button */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mt-8"
        >
          <Button
            onClick={onLiveDemo}
            className="bg-cyber-cyan text-black font-mono font-bold uppercase tracking-wider px-8 py-6 hover:bg-cyber-cyan/80 cyber-glow-hover transition-all btn-cyber"
          >
            <Terminal className="w-5 h-5 mr-2" />
            Try It Yourself
          </Button>
        </motion.div>
      </div>

      {/* Inline Footer for snap section */}
      <footer className="py-8 px-6 border-t border-white/10 mt-auto" data-testid="footer">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Bug className="w-6 h-6 text-cyber-cyan" />
            <span className="font-heading font-bold text-white">Sticky-Net</span>
          </div>

          <p className="text-gray-500 text-sm text-center">
            Built to waste scammers&apos; time, not yours. © 2026
          </p>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/heyitsguatham/sticky-net"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-white transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </footer>
    </section>
  );
};
