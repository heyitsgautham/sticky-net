import React, { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import "@/App.css";
import { motion, useInView, AnimatePresence } from "framer-motion";
import {
  Bug, Shield, Brain, Zap, Database, Drama, Terminal,
  MapPin, Smartphone, ChevronDown, Github, Menu, X,
  Play, Pause, Circle, RotateCcw, Settings, MessageSquare
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

// ============ ANIMATION VARIANTS ============
const fadeInUp = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" }
  }
};

const fadeInScale = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.6, ease: "easeOut" }
  }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const staggerItem = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" }
  }
};

// ============ SECTION IDS FOR NAVIGATION ============
const SECTIONS = [
  { id: 'hero', label: 'Home' },
  { id: 'problem', label: 'The Problem' },
  { id: 'solution', label: 'Solution' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'live-demo', label: 'Live Demo' },
];

// ============ NAVIGATION DOTS ============
const NavigationDots = ({ activeSection, onDotClick }) => {
  return (
    <div className="nav-dots">
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          onClick={() => onDotClick(section.id)}
          className={`nav-dot ${activeSection === section.id ? 'active' : ''}`}
          aria-label={`Go to ${section.label}`}
        >
          <span className="nav-dot-tooltip">{section.label}</span>
        </button>
      ))}
    </div>
  );
};

// ============ NAVIGATION ============
const Navigation = ({ onNavClick, onLiveDemo }) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (id) => {
    onNavClick?.(id);
    setIsMobileMenuOpen(false);
  };

  return (
    <nav
      data-testid="navigation"
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? "glass py-3" : "py-6"
        }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2" data-testid="logo">
          <Bug className="w-8 h-8 text-cyber-cyan" />
          <span className="font-heading font-bold text-xl text-white">Sticky-Net</span>
        </a>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-8">
          <button onClick={() => scrollTo("problem")} className="nav-link text-gray-400 hover:text-white transition-colors" data-testid="nav-problem">
            The Problem
          </button>
          <button onClick={() => scrollTo("solution")} className="nav-link text-gray-400 hover:text-white transition-colors" data-testid="nav-solution">
            Solution
          </button>
          <button onClick={() => scrollTo("architecture")} className="nav-link text-gray-400 hover:text-white transition-colors" data-testid="nav-architecture">
            Architecture
          </button>
          <button onClick={onLiveDemo} className="nav-link text-cyber-cyan hover:text-white transition-colors font-semibold" data-testid="nav-demo">
            Live Demo
          </button>
          <a
            href="https://github.com/heyitsguatham/sticky-net"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
            data-testid="nav-github"
          >
            <Github className="w-5 h-5" />
          </a>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden text-white"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          data-testid="mobile-menu-toggle"
        >
          {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden glass mt-2 mx-4 rounded-lg overflow-hidden"
          >
            <div className="flex flex-col p-4 gap-4">
              <button onClick={() => scrollTo("problem")} className="text-left text-gray-400 hover:text-white py-2">The Problem</button>
              <button onClick={() => scrollTo("solution")} className="text-left text-gray-400 hover:text-white py-2">Solution</button>
              <button onClick={() => scrollTo("architecture")} className="text-left text-gray-400 hover:text-white py-2">Architecture</button>
              <button onClick={() => { setIsMobileMenuOpen(false); onLiveDemo?.(); }} className="text-left text-cyber-cyan hover:text-white py-2 font-semibold">Live Demo</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

// ============ SPIDER WEB BACKGROUND ============
const SpiderWeb = () => {
  const [scammerDots, setScammerDots] = useState([]);
  const [isWebExpanded, setIsWebExpanded] = useState(false);

  // Trigger web expansion animation on mount
  useEffect(() => {
    const timer = setTimeout(() => setIsWebExpanded(true), 100);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const createDot = () => {
      const angle = Math.random() * 2 * Math.PI;
      const distance = 400 + Math.random() * 200;
      const startX = 50 + Math.cos(angle) * distance / 10;
      const startY = 50 + Math.sin(angle) * distance / 10;

      return {
        id: Date.now() + Math.random(),
        startX,
        startY,
        duration: 4 + Math.random() * 3,
      };
    };

    const interval = setInterval(() => {
      setScammerDots(prev => [...prev.slice(-8), createDot()]);
    }, 800);

    return () => clearInterval(interval);
  }, []);

  const webLines = [];
  const rings = 5;
  const spokes = 12;
  const centerX = 50;
  const centerY = 50;

  // Create radial spokes
  for (let i = 0; i < spokes; i++) {
    const angle = (i / spokes) * 2 * Math.PI;
    const endX = centerX + Math.cos(angle) * 45;
    const endY = centerY + Math.sin(angle) * 45;
    webLines.push({ x1: centerX, y1: centerY, x2: endX, y2: endY, key: `spoke-${i}` });
  }

  // Create concentric rings
  const ringPaths = [];
  for (let ring = 1; ring <= rings; ring++) {
    const radius = (ring / rings) * 45;
    let pathD = "";
    for (let spoke = 0; spoke <= spokes; spoke++) {
      const angle = (spoke / spokes) * 2 * Math.PI;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      pathD += `${spoke === 0 ? "M" : "L"} ${x} ${y} `;
    }
    pathD += "Z";
    ringPaths.push({ d: pathD, key: `ring-${ring}` });
  }

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <div className="hero-glow" />
      <svg
        className={`absolute inset-0 w-full h-full ${isWebExpanded ? 'web-expanded' : 'web-collapsed'}`}
        viewBox="0 0 100 100"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Web lines */}
        {webLines.map((line) => (
          <line
            key={line.key}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            className="spider-web-line pulse-line"
          />
        ))}
        {/* Rings */}
        {ringPaths.map((path, i) => (
          <path
            key={path.key}
            d={path.d}
            className="spider-web-line"
            style={{ animationDelay: `${i * 0.5}s` }}
          />
        ))}
        {/* Center node */}
        <circle cx={centerX} cy={centerY} r="1.5" className="spider-web-node" />
        {/* Intersection nodes */}
        {[1, 2, 3, 4, 5].map(ring =>
          Array.from({ length: spokes }).map((_, spoke) => {
            const radius = (ring / rings) * 45;
            const angle = (spoke / spokes) * 2 * Math.PI;
            return (
              <circle
                key={`node-${ring}-${spoke}`}
                cx={centerX + Math.cos(angle) * radius}
                cy={centerY + Math.sin(angle) * radius}
                r="0.4"
                className="spider-web-node"
                style={{ opacity: 0.4 }}
              />
            );
          })
        )}
      </svg>

      {/* Floating Scammer Dots */}
      {scammerDots.map((dot) => (
        <motion.div
          key={dot.id}
          className="absolute w-2 h-2 bg-cyber-red rounded-full danger-glow"
          initial={{
            left: `${dot.startX}%`,
            top: `${dot.startY}%`,
            opacity: 0,
            scale: 1
          }}
          animate={{
            left: "50%",
            top: "50%",
            opacity: [0, 1, 1, 0],
            scale: [1, 1, 0.5, 0]
          }}
          transition={{
            duration: dot.duration,
            ease: "easeIn"
          }}
        />
      ))}
    </div>
  );
};

// ============ ANIMATED COUNTER ============
const AnimatedCounter = ({ end, duration = 2, prefix = "", suffix = "" }) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;

    let startTime;
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [isInView, end, duration]);

  return (
    <span ref={ref} className="font-mono">
      {prefix}{count.toLocaleString()}{suffix}
    </span>
  );
};

// ============ FLUCTUATING COUNTER ============
const FluctuatingCounter = ({ base, range = 5 }) => {
  const [value, setValue] = useState(base);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });

  useEffect(() => {
    if (!isInView) return;
    const interval = setInterval(() => {
      setValue(base + Math.floor(Math.random() * range * 2) - range);
    }, 3000);
    return () => clearInterval(interval);
  }, [isInView, base, range]);

  return <span ref={ref} className="font-mono">{value.toLocaleString()}</span>;
};

// ============ HERO SECTION ============
const HeroSection = ({ onNavClick, onLiveDemo }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, amount: 0.5 });

  return (
    <section
      id="hero"
      className="snap-section relative flex flex-col items-center justify-center px-6 overflow-hidden"
      data-testid="hero-section"
    >
      <SpiderWeb />

      {/* Dark backdrop for better text readability */}
      <div className="hero-text-backdrop" />

      <motion.div
        ref={ref}
        variants={fadeInUp}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        className="relative z-10 text-center max-w-4xl hero-text-wrapper"
      >
        <Badge className="mb-6 border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10 font-mono" data-testid="hero-badge">
          AGENTIC AI HONEYPOT
        </Badge>

        <motion.h1
          variants={fadeInUp}
          className="font-heading text-4xl sm:text-5xl lg:text-7xl font-bold text-white mb-6 tracking-tight leading-tight"
        >
          The Honeypot That Wastes{" "}
          <span className="text-cyber-cyan">Their</span> Time,{" "}
          <br className="hidden sm:block" />
          Not <span className="text-cyber-red">Yours</span>.
        </motion.h1>

        <motion.p
          variants={fadeInUp}
          className="text-gray-400 text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed hero-description-blur"
        >
          AI-powered scam engagement that extracts intel while scammers wait.
        </motion.p>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
        >
          <motion.div variants={staggerItem}>
            <Button
              onClick={onLiveDemo}
              className="bg-cyber-cyan text-black font-mono font-bold uppercase tracking-wider px-8 py-6 hover:bg-cyber-cyan/80 cyber-glow-hover transition-all btn-cyber"
              data-testid="cta-see-action"
            >
              See It In Action
            </Button>
          </motion.div>
          <motion.div variants={staggerItem}>
            <Button
              variant="outline"
              onClick={() => onNavClick?.("architecture")}
              className="border-gray-600 text-gray-300 font-mono uppercase tracking-wider px-8 py-6 hover:bg-white/5 hover:border-gray-500 transition-all"
              data-testid="cta-view-architecture"
            >
              View Architecture
            </Button>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <ChevronDown className="w-6 h-6 text-gray-500 animate-bounce" />
        </motion.div>
      </motion.div>

      {/* Stats Row */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 w-full max-w-4xl mt-8"
        data-testid="stats-row"
      >
        {[
          { label: "Scams Trapped", value: 4247, prefix: "", suffix: "+" },
          { label: "UPIs Extracted", value: 1563, prefix: "", suffix: "" },
          { label: "Hours Wasted", value: 892, prefix: "", suffix: "h" },
          { label: "Active Threats", value: 47, isFluctuating: true },
        ].map((stat, i) => (
          <motion.div key={stat.label} variants={staggerItem}>
            <Card className="stat-card glass border-white/10 hover:border-cyber-cyan/30" data-testid={`stat-card-${i}`}>
              <CardContent className="p-4 md:p-6 text-center">
                <div className="text-2xl md:text-3xl font-bold text-white mb-1">
                  {stat.isFluctuating ? (
                    <FluctuatingCounter base={stat.value} />
                  ) : (
                    <AnimatedCounter end={stat.value} prefix={stat.prefix} suffix={stat.suffix} />
                  )}
                </div>
                <div className="text-xs md:text-sm text-gray-500 uppercase tracking-wide">{stat.label}</div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
};

// ============ PROBLEM SECTION (India Heatmap) ============
const RupeeRain = () => {
  const [rupees] = useState(() =>
    Array.from({ length: 20 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 10,
      duration: 8 + Math.random() * 6,
      size: 12 + Math.random() * 8,
    }))
  );

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-30">
      {rupees.map((r) => (
        <div
          key={r.id}
          className="absolute text-cyber-red font-mono rupee-rain"
          style={{
            left: `${r.left}%`,
            fontSize: `${r.size}px`,
            animationDelay: `${r.delay}s`,
            animationDuration: `${r.duration}s`,
          }}
        >
          ₹
        </div>
      ))}
    </div>
  );
};

const IndiaMap = () => {
  const [hoveredState, setHoveredState] = useState(null);

  // Import India map data directly
  const India = require('@svg-maps/india').default;

  // Scam hotspot states (higher fraud rates)
  const hotspotStates = ['dl', 'mh', 'wb', 'ka', 'tg', 'tn', 'up', 'rj', 'gj'];

  return (
    <div className="relative w-full max-w-md">
      <svg
        viewBox={India.viewBox}
        className="w-full h-auto"
        aria-label={India.label}
      >
        {/* Render each state */}
        {India.locations.map((location) => {
          const isHotspot = hotspotStates.includes(location.id);
          const isHovered = hoveredState === location.id;

          return (
            <path
              key={location.id}
              id={location.id}
              d={location.path}
              fill={isHovered ? 'rgba(255, 51, 102, 0.5)' : isHotspot ? 'rgba(255, 51, 102, 0.25)' : 'rgba(255, 51, 102, 0.1)'}
              stroke="#FF3366"
              strokeWidth={isHovered ? "1.5" : "0.5"}
              style={{
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                opacity: isHovered ? 1 : isHotspot ? 0.9 : 0.7,
              }}
              onMouseEnter={() => setHoveredState(location.id)}
              onMouseLeave={() => setHoveredState(null)}
            />
          );
        })}
      </svg>

      {/* State name tooltip */}
      {hoveredState && (
        <div className="absolute top-2 left-2 bg-black/90 text-cyber-red text-xs px-2 py-1 rounded border border-cyber-red/50 font-mono">
          {India.locations.find(l => l.id === hoveredState)?.name || hoveredState.toUpperCase()}
        </div>
      )}
    </div>
  );
};

const ProblemSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, amount: 0.5 });

  return (
    <section
      id="problem"
      className="snap-section relative px-6 overflow-hidden flex items-center"
      data-testid="problem-section"
    >
      <RupeeRain />

      <div ref={ref} className="max-w-7xl mx-auto w-full">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-12"
        >
          <Badge className="mb-4 border-cyber-red text-cyber-red bg-cyber-red/10 font-mono" data-testid="problem-badge">
            THE PROBLEM
          </Badge>
          <h2 className="font-heading text-3xl md:text-5xl font-bold text-white">
            India's Silent Financial Epidemic
          </h2>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8 md:gap-12 items-center">
          <motion.div
            variants={fadeInScale}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="flex justify-start"
          >
            <IndiaMap />
          </motion.div>

          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate={isInView ? "visible" : "hidden"}
            className="space-y-6"
          >
            <motion.div variants={staggerItem} data-testid="stat-fraud-loss">
              <div className="text-4xl md:text-5xl font-heading font-bold text-cyber-red mb-2">
                ₹<AnimatedCounter end={60000} duration={2.5} />Cr+
              </div>
              <p className="text-gray-400 text-base md:text-lg">Lost to digital fraud annually</p>
            </motion.div>

            <motion.div variants={staggerItem} data-testid="stat-victims">
              <div className="text-4xl md:text-5xl font-heading font-bold text-white mb-2">
                <AnimatedCounter end={1200000} duration={2.5} suffix="+" />
              </div>
              <p className="text-gray-400 text-base md:text-lg">Victims every year</p>
            </motion.div>

            <motion.div variants={staggerItem} className="pt-2">
              <p className="text-gray-500 leading-relaxed text-sm md:text-base">
                While victims lose their life savings in minutes, scammers operate with impunity from
                underground call centers. Traditional defenses are reactive. We flip the script.
              </p>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};

// ============ SOLUTION SECTION (Split Screen) ============
const WhatsAppMock = () => {
  const messages = [
    { type: "incoming", text: "Dear Customer, Your SBI account will be BLOCKED within 24 hours due to incomplete KYC verification. Update immediately to avoid account suspension.", time: "10:31 AM" },
    { type: "outgoing", text: "oh god sir pls dont block my account. my pension comes in sbi only. i am old lady i dont understand what is kyc. what i have to do? pls tell me", time: "10:32 AM" },
    { type: "incoming", text: "This is urgent matter. I am calling from SBI head office Mumbai. Your account ending 4521 is showing KYC pending.", time: "10:33 AM" },
    { type: "outgoing", text: "hello beta i am very worried. i cannot come to mumbai i live in pune. my knees are bad i cannot walk much. how can i do this verification from home?", time: "10:34 AM" },
    { type: "incoming", text: "Please share your registered mobile number. Or you can directly update by paying Rs.10 verification fee to UPI ID: sbi.kyc.update@ybl", time: "10:35 AM" },
    { type: "outgoing", text: "ok beta i will pay 10 rs right now. i am opening my phone pay app... what name should show on screen? i want to be sure it is going to bank only.", time: "10:37 AM" },
  ];

  return (
    <div className="bg-[#0B141A] rounded-xl overflow-hidden border border-white/10 max-w-sm mx-auto" data-testid="whatsapp-mock">
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

const TerminalAnalysis = () => {
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
            className={`mb-2 ${log.type === "ai" ? "text-cyber-cyan" :
              log.type === "extract" ? "text-yellow-400" :
                "text-gray-500"
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

const SolutionSection = () => {
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
          <Badge className="mb-4 border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10 font-mono" data-testid="solution-badge">
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
              <span className="text-sm text-gray-400 font-mono uppercase">What&apos;s Really Happening</span>
            </div>
            <TerminalAnalysis />
          </motion.div>
        </div>
      </div>
    </section>
  );
};

// ============ TECH STACK (Bento Grid) ============
const TechStackSection = () => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: false, amount: 0.5 });

  const cards = [
    {
      title: "The Brain",
      subtitle: (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-cyber-cyan to-blue-400 animate-pulse" />
            <span className="font-heading text-lg md:text-xl font-bold bg-gradient-to-r from-cyber-cyan to-blue-300 bg-clip-text text-transparent">
              Gemini 3 Flash
            </span>
            <span className="text-xs text-gray-500 font-mono px-2 py-0.5 rounded bg-gray-800/50 border border-gray-700">Lightning Triage</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-400 to-pink-400 animate-pulse" style={{ animationDelay: '0.3s' }} />
            <span className="font-heading text-lg md:text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-300 bg-clip-text text-transparent">
              Gemini 3 Pro
            </span>
            <span className="text-xs text-gray-500 font-mono px-2 py-0.5 rounded bg-gray-800/50 border border-gray-700">Strategic Response</span>
          </div>
          <div className="mt-3 pt-2 border-t border-white/10">
            <span className="text-cyber-cyan font-semibold text-sm">Detect & Respond</span>
          </div>
          <div className="space-y-3 text-base leading-relaxed mt-3">
            <div className="flex items-start gap-3">
              <Zap className="w-5 h-5 text-cyber-cyan mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Flash-speed triage:</span> <span className="text-gray-400">97.2% accuracy in 150ms</span></span>
            </div>
            <div className="flex items-start gap-3">
              <Brain className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Deep reasoning:</span> <span className="text-gray-400">Persona-perfect response generation</span></span>
            </div>
            <div className="flex items-start gap-3">
              <Settings className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Hybrid intelligence:</span> <span className="text-gray-400">Regex pre-filter + AI classifier</span></span>
            </div>
            <div className="flex items-start gap-3">
              <MessageSquare className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Context-aware:</span> <span className="text-gray-400">Full conversation history analysis</span></span>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Adaptive responses:</span> <span className="text-gray-400">Real-time strategy adjustment</span></span>
            </div>
            <div className="flex items-start gap-3">
              <Zap className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Multi-turn engagement:</span> <span className="text-gray-400">Extended conversation tactics</span></span>
            </div>
            <div className="flex items-start gap-3">
              <Terminal className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
              <span><span className="font-semibold text-white">Exit strategy:</span> <span className="text-gray-400">Graceful disengagement protocols</span></span>
            </div>
          </div>
        </div>
      ),
      purpose: null,
      description: null,
      icon: Brain,
      className: "md:col-span-2 md:row-span-2",
      iconColor: "text-cyber-cyan",
    },
    {
      title: "The Flow",
      subtitle: "One-Pass Architecture",
      purpose: "Single Unified Inference",
      description: "Single inference for detection, persona selection, and response.",
      icon: Zap,
      className: "md:col-span-1",
      iconColor: "text-yellow-400",
    },
    {
      title: "The Trap",
      subtitle: "Dynamic Personas",
      purpose: "Believable Human Mimicry",
      description: "10+ pre-trained personas from confused grandma to tech-illiterate uncle.",
      icon: Drama,
      className: "md:col-span-1",
      iconColor: "text-purple-400",
    },
    {
      title: "The Intel",
      subtitle: "Real-time Extraction",
      purpose: "Capture Scammer Data",
      description: "Auto-capture UPIs, phone numbers, and scammer fingerprints.",
      icon: Database,
      className: "md:col-span-2",
      iconColor: "text-green-400",
    },
  ];

  return (
    <section
      id="architecture"
      className="snap-section px-6 flex items-center"
      data-testid="architecture-section"
    >
      <div ref={ref} className="max-w-7xl mx-auto w-full">
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="text-center mb-12"
        >
          <Badge className="mb-4 border-white/30 text-gray-300 bg-white/5 font-mono" data-testid="architecture-badge">
            ARCHITECTURE
          </Badge>
          <h2 className="font-heading text-3xl md:text-5xl font-bold text-white">
            Built for Speed & Deception
          </h2>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate={isInView ? "visible" : "hidden"}
          className="grid md:grid-cols-4 gap-4 md:gap-6"
        >
          {cards.map((card, i) => (
            <motion.div
              key={card.title}
              variants={staggerItem}
              className={card.className}
              data-testid={`bento-card-${i}`}
            >
              <Card className="bento-card h-full glass border-white/10">
                <CardContent className="p-6 md:p-8 h-full flex flex-col">
                  {React.createElement(card.icon, { className: `w-10 h-10 ${card.iconColor} mb-4` })}
                  <div className="text-xs text-gray-500 font-mono uppercase tracking-wider mb-1">
                    {card.title}
                  </div>
                  <h3 className="font-heading text-xl md:text-2xl font-bold text-white mb-2">
                    {card.subtitle}
                  </h3>
                  {card.purpose && (
                    <div className="text-sm font-semibold text-cyber-cyan mb-3">
                      {card.purpose}
                    </div>
                  )}
                  <p className="text-gray-400 text-sm leading-relaxed mt-auto">
                    {card.description}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

// ============ LIVE DEMO (Terminal) ============
const demoConversation = [
  { speaker: 'system', text: '━━━ SESSION #4821 STARTED ━━━', delay: 0 },
  { speaker: 'system', text: 'Target: +91-98XXX-XX412', delay: 500 },
  { speaker: 'system', text: 'Persona Active: PUSHPA_VERMA (grandmother)', delay: 800 },
  { speaker: 'system', text: '', delay: 1000 },
  { speaker: 'scammer', text: '[SCAMMER]: Hello madam, I am calling from SBI bank', delay: 1500 },
  { speaker: 'scammer', text: '[SCAMMER]: Your account will be blocked. Share OTP to verify.', delay: 2500 },
  { speaker: 'system', text: '> THREAT_ANALYSIS: Bank impersonation detected (97.2%)', delay: 3500 },
  { speaker: 'system', text: '> STRATEGY: Express confusion, request clarification', delay: 4000 },
  { speaker: 'ai', text: '[PUSHPA]: Arrey beta, which SBI? I have account in Punjab National Bank...', delay: 4500 },
  { speaker: 'scammer', text: '[SCAMMER]: Madam this is central office. All banks connected.', delay: 5500 },
  { speaker: 'ai', text: '[PUSHPA]: Oh achha? My husband used to handle all this. He is no more 😢', delay: 6500 },
  { speaker: 'system', text: '> TACTIC: Emotional delay deployed (+45 seconds gained)', delay: 7500 },
  { speaker: 'scammer', text: '[SCAMMER]: Sorry madam. But urgent. OTP please or money gone.', delay: 8500 },
  { speaker: 'ai', text: '[PUSHPA]: Beta wait, my phone is showing many numbers...', delay: 9500 },
  { speaker: 'ai', text: '[PUSHPA]: One says 847291, one says 552183... which one you need?', delay: 10500 },
  { speaker: 'system', text: '> BAIT_DEPLOYED: Fake OTP sequence', delay: 11500 },
  { speaker: 'system', text: '> EXTRACTING: Voice pattern analysis...', delay: 12000 },
  { speaker: 'scammer', text: '[SCAMMER]: 847291 madam! Quick quick!', delay: 12500 },
  { speaker: 'system', text: '> BEHAVIOR_LOGGED: High urgency tactics', delay: 13500 },
  { speaker: 'ai', text: '[PUSHPA]: Oh wait beta, my daughter is calling on other phone...', delay: 14000 },
  { speaker: 'ai', text: '[PUSHPA]: Can I call you back? What is your number?', delay: 14800 },
  { speaker: 'system', text: '> INTEL_ATTEMPT: Phone number extraction initiated', delay: 15500 },
  { speaker: 'scammer', text: '[SCAMMER]: No madam no callback. Just tell OTP now.', delay: 16500 },
  { speaker: 'system', text: '> SCAM_INDICATOR: Callback refusal logged', delay: 17500 },
  { speaker: 'ai', text: '[PUSHPA]: Beta, at least tell UPI ID. I will send ₹1 to verify you are real bank.', delay: 18500 },
  { speaker: 'scammer', text: '[SCAMMER]: OK madam. UPI is bank.verify@ybl', delay: 19500 },
  { speaker: 'system', text: '> ✓ UPI_EXTRACTED: bank.verify@ybl', delay: 20500 },
  { speaker: 'system', text: '> ✓ FLAGGED: Suspicious UPI pattern detected', delay: 21000 },
  { speaker: 'system', text: '', delay: 21500 },
  { speaker: 'system', text: '━━━ SESSION SUMMARY ━━━', delay: 22000 },
  { speaker: 'system', text: 'Duration: 8 minutes 23 seconds', delay: 22500 },
  { speaker: 'system', text: 'Intel Captured: Phone, UPI ID, Voice Pattern, Tactics', delay: 23000 },
  { speaker: 'system', text: 'Status: SCAMMER WASTED ✓', delay: 23500 },
];

const LiveTerminal = () => {
  const terminalRef = useRef(null);
  const [logs, setLogs] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!isPlaying || currentIndex >= demoConversation.length) return;

    const currentLog = demoConversation[currentIndex];
    const delay = currentIndex === 0 ? 500 : currentLog.delay - (demoConversation[currentIndex - 1]?.delay || 0);

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
      case 'scammer': return 'text-cyber-red';
      case 'ai': return 'text-cyber-cyan';
      case 'system': return 'text-gray-500';
      default: return 'text-gray-400';
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
              className={`w-2 h-2 ${isPlaying ? 'text-green-500' : 'text-gray-500'}`}
              fill="currentColor"
            />
            <span className={`text-xs font-mono ${isPlaying ? 'text-green-500' : 'text-gray-500'}`}>
              {isPlaying ? 'LIVE' : isComplete ? 'COMPLETE' : 'PAUSED'}
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
              className={`h-8 px-3 ${isPlaying ? 'text-yellow-500 hover:text-yellow-400' : 'text-green-500 hover:text-green-400'}`}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4 mr-1" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1" />
                  {isComplete ? 'Replay' : 'Play'}
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={terminalRef}
        className="terminal-body h-96 overflow-y-auto scroll-smooth"
      >
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
                className={`mb-1 ${getSpeakerColor(log.speaker)} ${log.text === '' ? 'h-4' : ''}`}
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

const LiveDemoSection = ({ onLiveDemo }) => {
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
          <Badge className="mb-4 border-green-500 text-green-500 bg-green-500/10 font-mono" data-testid="live-demo-badge">
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
            <a href="https://github.com/heyitsguatham/sticky-net" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </footer>
    </section>
  );
};

// ============ MAIN APP ============
function App() {
  const containerRef = useRef(null);
  const navigate = useNavigate();
  const [activeSection, setActiveSection] = useState('hero');

  // Track active section on scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const sections = SECTIONS.map(s => document.getElementById(s.id));
      const containerTop = container.scrollTop;
      const viewportHeight = window.innerHeight;

      for (let i = sections.length - 1; i >= 0; i--) {
        const section = sections[i];
        if (section) {
          const sectionTop = section.offsetTop;
          if (containerTop >= sectionTop - viewportHeight / 2) {
            setActiveSection(SECTIONS[i].id);
            break;
          }
        }
      }
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = useCallback((id) => {
    const section = document.getElementById(id);
    if (section && containerRef.current) {
      section.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  const goToLiveDemo = useCallback(() => {
    navigate('/chat');
  }, [navigate]);

  return (
    <div
      ref={containerRef}
      className="snap-container scrollbar-hide bg-cyber-obsidian"
    >
      <Navigation onNavClick={scrollToSection} onLiveDemo={goToLiveDemo} />
      <NavigationDots activeSection={activeSection} onDotClick={scrollToSection} />

      <HeroSection onNavClick={scrollToSection} onLiveDemo={goToLiveDemo} />
      <ProblemSection />
      <SolutionSection />
      <TechStackSection />
      <LiveDemoSection onLiveDemo={goToLiveDemo} />
    </div>
  );
}

export default App;
