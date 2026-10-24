import "@/App.css";
import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { SECTIONS, NavigationDots, Navigation } from "@/components/landing/Navigation";
import { HeroSection } from "@/components/landing/HeroSection";
import { LiveDemoSection } from "@/components/landing/LiveDemoSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { SolutionSection } from "@/components/landing/SolutionSection";
import { TechStackSection } from "@/components/landing/TechStackSection";

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
