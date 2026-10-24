// Landing hero with the headline stats and calls to action.
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fadeInUp, staggerContainer, staggerItem } from "@/components/landing/motion";
import { AnimatedCounter, FluctuatingCounter } from "@/components/landing/Counters";
import { SpiderWeb } from "@/components/landing/SpiderWeb";

// ============ HERO SECTION ============
export const HeroSection = ({ onNavClick, onLiveDemo }) => {
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
