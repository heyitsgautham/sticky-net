// Top bar and side dots that jump between landing page sections.
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bug, Github, Menu, X } from "lucide-react";

// ============ SECTION IDS FOR NAVIGATION ============
export const SECTIONS = [
  { id: "hero", label: "Home" },
  { id: "problem", label: "The Problem" },
  { id: "solution", label: "Solution" },
  { id: "architecture", label: "Architecture" },
  { id: "live-demo", label: "Live Demo" },
];

// ============ NAVIGATION DOTS ============
export const NavigationDots = ({ activeSection, onDotClick }) => {
  return (
    <div className="nav-dots">
      {SECTIONS.map((section) => (
        <button
          key={section.id}
          onClick={() => onDotClick(section.id)}
          className={`nav-dot ${activeSection === section.id ? "active" : ""}`}
          aria-label={`Go to ${section.label}`}
        >
          <span className="nav-dot-tooltip">{section.label}</span>
        </button>
      ))}
    </div>
  );
};

// ============ NAVIGATION ============
export const Navigation = ({ onNavClick, onLiveDemo }) => {
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
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled ? "glass py-3" : "py-6"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        <a href="/" className="flex items-center gap-2" data-testid="logo">
          <Bug className="w-8 h-8 text-cyber-cyan" />
          <span className="font-heading font-bold text-xl text-white">Sticky-Net</span>
        </a>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-8">
          <button
            onClick={() => scrollTo("problem")}
            className="nav-link text-gray-400 hover:text-white transition-colors"
            data-testid="nav-problem"
          >
            The Problem
          </button>
          <button
            onClick={() => scrollTo("solution")}
            className="nav-link text-gray-400 hover:text-white transition-colors"
            data-testid="nav-solution"
          >
            Solution
          </button>
          <button
            onClick={() => scrollTo("architecture")}
            className="nav-link text-gray-400 hover:text-white transition-colors"
            data-testid="nav-architecture"
          >
            Architecture
          </button>
          <button
            onClick={onLiveDemo}
            className="nav-link text-cyber-cyan hover:text-white transition-colors font-semibold"
            data-testid="nav-demo"
          >
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
              <button
                onClick={() => scrollTo("problem")}
                className="text-left text-gray-400 hover:text-white py-2"
              >
                The Problem
              </button>
              <button
                onClick={() => scrollTo("solution")}
                className="text-left text-gray-400 hover:text-white py-2"
              >
                Solution
              </button>
              <button
                onClick={() => scrollTo("architecture")}
                className="text-left text-gray-400 hover:text-white py-2"
              >
                Architecture
              </button>
              <button
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  onLiveDemo?.();
                }}
                className="text-left text-cyber-cyan hover:text-white py-2 font-semibold"
              >
                Live Demo
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};
