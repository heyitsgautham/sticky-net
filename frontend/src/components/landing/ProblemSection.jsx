// Scam-losses section with the rupee rain and India map.
import { useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { fadeInUp, fadeInScale, staggerContainer, staggerItem } from "@/components/landing/motion";
import { AnimatedCounter } from "@/components/landing/Counters";
import India from "@svg-maps/india";

// ============ PROBLEM SECTION (India Heatmap) ============
export const RupeeRain = () => {
  const [rupees] = useState(() =>
    Array.from({ length: 20 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      delay: Math.random() * 10,
      duration: 8 + Math.random() * 6,
      size: 12 + Math.random() * 8,
    })),
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

export const IndiaMap = () => {
  const [hoveredState, setHoveredState] = useState(null);

  // Scam hotspot states (higher fraud rates)
  const hotspotStates = ["dl", "mh", "wb", "ka", "tg", "tn", "up", "rj", "gj"];

  return (
    <div className="relative w-full max-w-md">
      <svg viewBox={India.viewBox} className="w-full h-auto" aria-label={India.label}>
        {/* Render each state */}
        {India.locations.map((location) => {
          const isHotspot = hotspotStates.includes(location.id);
          const isHovered = hoveredState === location.id;

          return (
            <path
              key={location.id}
              id={location.id}
              d={location.path}
              fill={
                isHovered
                  ? "rgba(255, 51, 102, 0.5)"
                  : isHotspot
                    ? "rgba(255, 51, 102, 0.25)"
                    : "rgba(255, 51, 102, 0.1)"
              }
              stroke="#FF3366"
              strokeWidth={isHovered ? "1.5" : "0.5"}
              style={{
                cursor: "pointer",
                transition: "all 0.2s ease",
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
          {India.locations.find((l) => l.id === hoveredState)?.name || hoveredState.toUpperCase()}
        </div>
      )}
    </div>
  );
};

export const ProblemSection = () => {
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
          <Badge
            className="mb-4 border-cyber-red text-cyber-red bg-cyber-red/10 font-mono"
            data-testid="problem-badge"
          >
            THE PROBLEM
          </Badge>
          <h2 className="font-heading text-3xl md:text-5xl font-bold text-white">
            India&apos;s Silent Financial Epidemic
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
                ₹<AnimatedCounter end={60000} duration={2.5} />
                Cr+
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
                While victims lose their life savings in minutes, scammers operate with impunity
                from underground call centers. Traditional defenses are reactive. We flip the
                script.
              </p>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
