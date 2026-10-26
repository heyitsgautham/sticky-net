// Animated spider web backdrop behind the hero section.
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

// ============ SPIDER WEB BACKGROUND ============
export const SpiderWeb = () => {
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
      const startX = 50 + (Math.cos(angle) * distance) / 10;
      const startY = 50 + (Math.sin(angle) * distance) / 10;

      return {
        id: Date.now() + Math.random(),
        startX,
        startY,
        duration: 4 + Math.random() * 3,
      };
    };

    const interval = setInterval(() => {
      setScammerDots((prev) => [...prev.slice(-8), createDot()]);
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
        className={`absolute inset-0 w-full h-full ${isWebExpanded ? "web-expanded" : "web-collapsed"}`}
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
        {[1, 2, 3, 4, 5].map((ring) =>
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
          }),
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
            scale: 1,
          }}
          animate={{
            left: "50%",
            top: "50%",
            opacity: [0, 1, 1, 0],
            scale: [1, 1, 0.5, 0],
          }}
          transition={{
            duration: dot.duration,
            ease: "easeIn",
          }}
        />
      ))}
    </div>
  );
};
