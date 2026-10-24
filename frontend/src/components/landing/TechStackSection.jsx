// Architecture and tech stack cards.
import React from "react";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Shield, Brain, Zap, Database, Drama, Terminal, Settings, MessageSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fadeInUp, staggerContainer, staggerItem } from "@/components/landing/motion";

// ============ TECH STACK (Bento Grid) ============
export const TechStackSection = () => {
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
