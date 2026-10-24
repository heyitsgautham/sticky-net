// Number counters that animate into view.
import { useEffect, useState, useRef } from "react";
import { useInView } from "framer-motion";

// ============ ANIMATED COUNTER ============
export const AnimatedCounter = ({ end, duration = 2, prefix = "", suffix = "" }) => {
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
export const FluctuatingCounter = ({ base, range = 5 }) => {
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
