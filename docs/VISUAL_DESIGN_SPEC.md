# Sticky-Net: Visual Design Specification
### Landing Page — "The Trap That Bites Back"

---

## 🎯 Design Philosophy

**Aesthetic Direction:** Dark-mode Cyberpunk meets Enterprise Security  
**Inspiration:** Vercel's minimalism × Linear's polish × Wiz's security gravitas  
**Core Metaphor:** A digital spider's web that ensnares scammers in real-time

---

## 🎨 Color Palette

### Primary Colors
| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| **Background Deep** | Obsidian Black | `#0A0A0B` | Main page background |
| **Background Elevated** | Carbon Gray | `#111113` | Cards, modals |
| **Background Subtle** | Graphite | `#18181B` | Hover states, borders |

### Accent Colors
| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| **Primary Glow** | Electric Cyan | `#00F5D4` | CTAs, active states, success |
| **Danger/Alert** | Threat Red | `#FF3366` | Scam indicators, warnings |
| **Intel Highlight** | Gold Amber | `#FFB800` | Extracted intelligence |
| **Secondary** | Phantom Purple | `#7B61FF` | Secondary accents |

### Text Hierarchy
| Role | Color | Hex |
|------|-------|-----|
| **Headline** | Pure White | `#FFFFFF` |
| **Body** | Silver | `#A1A1AA` |
| **Muted** | Zinc | `#71717A` |
| **Code/Mono** | Matrix Green | `#4ADE80` |

### Gradients
```css
/* Hero Gradient */
--gradient-hero: linear-gradient(135deg, #0A0A0B 0%, #1a1a2e 50%, #0A0A0B 100%);

/* Glow Effect */
--glow-cyan: 0 0 40px rgba(0, 245, 212, 0.3);
--glow-red: 0 0 40px rgba(255, 51, 102, 0.3);

/* Card Border Gradient */
--border-gradient: linear-gradient(135deg, #00F5D4 0%, #7B61FF 100%);
```

---

## 🕷️ Section 1: Hero — "The Live Trap"

### Visual Concept
A full-viewport hero featuring an **animated spider web** made of glowing cyan lines on the dark background. At the center sits the Sticky-Net logo—a stylized spider icon. As users scroll, **red dots (representing scammers)** appear at the edges of the screen and slowly drift toward the center, getting "caught" in the web.

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│     ╭─────────────────────────────────────────────────────────╮    │
│     │              [Animated Spider Web SVG]                  │    │
│     │                                                         │    │
│     │                     STICKY-NET                          │    │
│     │                                                         │    │
│     │           "The Honeypot That Wastes Their Time,         │    │
│     │                 Not Yours."                             │    │
│     │                                                         │    │
│     │   [ See It In Action ↓ ]    [ View Architecture → ]     │    │
│     │                                                         │    │
│     ╰─────────────────────────────────────────────────────────╯    │
│                                                                    │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│   │ 47 Scams │ │ 2.3 Hrs  │ │ 156 UPIs │ │ 99.2%    │              │
│   │ Trapped  │ │ Wasted   │ │ Extracted│ │ Accuracy │              │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                    │
│                        ▼ Scroll to explore                         │
└────────────────────────────────────────────────────────────────────┘
```

### Copywriting
- **Tagline:** "The Honeypot That Wastes Their Time, Not Yours."
- **Sub-tagline:** "AI-powered scam engagement that extracts intel while scammers wait."
- **CTA Primary:** "See It In Action ↓"
- **CTA Secondary:** "View Architecture →"

### Animations
1. **Web Pulse:** Subtle pulse animation on web lines (2s ease-in-out infinite)
2. **Scammer Dots:** Red particles drift from edges, slowing as they near center
3. **Stats Counter:** Numbers count up on viewport entry
4. **Parallax:** Web scales subtly on scroll

---

## 🔥 Section 2: The Problem — "India's ₹60 Crore Crisis"

### Visual Concept
A **dark data visualization** showing the scale of fraud. Features an animated **heat map of India** with pulsing red hotspots representing fraud activity. Numbers cascade down like The Matrix, but in rupee symbols (₹).

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   THE PROBLEM                                                      │
│   ━━━━━━━━━━━━━━                                                   │
│                                                                    │
│   ┌─────────────────────────────────────┐  ┌────────────────────┐ │
│   │                                     │  │                    │ │
│   │     [Animated India Heatmap]        │  │  ₹60,000 Cr+       │ │
│   │                                     │  │  Lost to fraud     │ │
│   │     🔴 Mumbai    🔴 Delhi           │  │  in 2024 alone     │ │
│   │          🔴 Bangalore               │  │                    │ │
│   │     🔴 Hyderabad                    │  │  ─────────────     │ │
│   │                                     │  │                    │ │
│   │     Real-time fraud pings           │  │  1.2M+ victims     │ │
│   │                                     │  │  per month         │ │
│   └─────────────────────────────────────┘  │                    │ │
│                                            │  12 mins avg       │ │
│   "Every 12 seconds, another Indian        │  per scam call     │ │
│    loses money to a scammer."              │                    │ │
│                                            └────────────────────┘ │
│                                                                    │
│   ┌──────────────────────────────────────────────────────────────┐│
│   │ 🔴 "Your KYC expired"  🔴 "Lottery winner"  🔴 "SBI block"  ││
│   │              [Scrolling scam message ticker]                 ││
│   └──────────────────────────────────────────────────────────────┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Copywriting
- **Section Label:** `THE PROBLEM` (small, muted, uppercase)
- **Headline:** "Every 12 Seconds, Another Victim."
- **Subhead:** "₹60,000 Cr+ lost to digital fraud in India. Scammers operate with impunity because nobody wastes *their* time."
- **Stat Cards:**
  - "₹60,000 Cr+" — "Lost to fraud in 2024"
  - "1.2M+" — "Victims per month"
  - "12 mins" — "Average scam duration"

### Animations
1. **Heatmap Pulse:** Red circles pulse on major cities
2. **Rupee Rain:** ₹ symbols fall in background (Matrix-style, subtle)
3. **Scam Ticker:** Horizontal scroll of real scam message examples

---

## 🎭 Section 3: The Solution — "Meet Pushpa Verma"

### Visual Concept
A **split-screen reveal** showing the duality of the system. On the left: a warm, innocent WhatsApp-style chat interface showing "Pushpa" responding to scammers. On the right: a cold, technical terminal showing the AI's real-time analysis.

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   THE SOLUTION                                                     │
│   ━━━━━━━━━━━━━━━                                                 │
│                                                                    │
│   "What Scammers See"              "What We See"                  │
│                                                                    │
│   ┌─────────────────────────┐    ┌─────────────────────────────┐  │
│   │  📱 WhatsApp Chat       │    │  🖥️ Intelligence Terminal    │  │
│   │  ─────────────────────  │    │  ───────────────────────    │  │
│   │                         │    │                             │  │
│   │  👤 Scammer:            │    │  > SCAM_DETECTED: 0.94      │  │
│   │  "Madam your account    │    │  > TYPE: banking_fraud      │  │
│   │   will be blocked..."   │    │  > PERSONA: pushpa_verma    │  │
│   │                         │    │  > STRATEGY: naive_trust    │  │
│   │  👵 Pushpa Verma:       │    │                             │  │
│   │  "Oh no beta! I am      │    │  > EXTRACTING...            │  │
│   │   very worried. Which   │    │  > UPI_ID: scam@paytm ✓     │  │
│   │   account number?"      │    │  > BANK: HDFC ****4521 ✓    │  │
│   │                         │    │  > TIME_WASTED: 00:23:47    │  │
│   │  👤 Scammer:            │    │                             │  │
│   │  "Send to this UPI:     │    │  > STATUS: ENGAGED          │  │
│   │   help@support..."      │    │  > [██████████░░] 85%       │  │
│   │                         │    │                             │  │
│   └─────────────────────────┘    └─────────────────────────────┘  │
│                                                                    │
│                     ↓ See the full architecture                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Copywriting
- **Section Label:** `THE SOLUTION`
- **Headline:** "Meet Pushpa Verma. She's Not Real. But Her Impact Is."
- **Subhead:** "An AI persona so convincing, scammers spend hours trying to defraud her—while we extract their bank accounts, UPI IDs, and networks."
- **Left Panel Title:** "What Scammers See" — A worried grandmother
- **Right Panel Title:** "What We See" — A precision intelligence operation

### Persona Card (Below)
```
┌────────────────────────────────────────────────────────────────────┐
│  👵 PUSHPA VERMA                                                   │
│  ────────────────                                                  │
│  Age: 68  •  Location: Varanasi  •  Status: Widowed               │
│  Traits: Trusting, Confused by Technology, Recently Learned UPI   │
│                                                                    │
│  "Beta, I don't understand these things. Can you help?"           │
│                                                                    │
│  [Why This Works →]                                                │
└────────────────────────────────────────────────────────────────────┘
```

### Animations
1. **Chat Typewriter:** Messages appear with typing animation
2. **Terminal Scroll:** Green text streams in real-time
3. **Intel Highlight:** Extracted data glows gold when captured
4. **Progress Bar:** Slowly fills as engagement continues

---

## ⚙️ Section 4: Tech Stack — "One-Pass Architecture"

### Visual Concept
A **Bento Grid** layout (inspired by Apple's design) showing the technical components as interconnected cards. The central card features the architecture flow, surrounded by smaller component cards.

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   THE ARCHITECTURE                                                 │
│   ━━━━━━━━━━━━━━━━━━                                              │
│                                                                    │
│   "One Model. One Pass. Zero Latency."                            │
│                                                                    │
│   ┌─────────────────────────────────────┬─────────────────────┐   │
│   │                                     │                     │   │
│   │   ┌─────┐    ┌─────┐    ┌─────┐    │   🧠 GEMINI 2.5     │   │
│   │   │ MSG │ →  │ AI  │ →  │ OUT │    │   ─────────────     │   │
│   │   └─────┘    └─────┘    └─────┘    │   Flash for speed   │   │
│   │                                     │   Pro for depth     │   │
│   │   [ONE-PASS ARCHITECTURE DIAGRAM]   │                     │   │
│   │                                     │   < 2s response     │   │
│   │   Message → Classify + Extract      │                     │   │
│   │           + Respond in ONE call     │                     │   │
│   │                                     │                     │   │
│   ├─────────────────────────────────────┴─────────────────────┤   │
│   │                                                           │   │
│   │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐ │   │
│   │  │ 🔍 DETECTION  │  │ 🎭 PERSONAS   │  │ 💰 INTEL      │ │   │
│   │  │               │  │               │  │               │ │   │
│   │  │ Regex Pre-    │  │ Pushpa Verma  │  │ Bank Account  │ │   │
│   │  │ Filter +      │  │ Dynamic       │  │ UPI ID        │ │   │
│   │  │ ML Classifier │  │ Adaptation    │  │ Phishing URL  │ │   │
│   │  │               │  │               │  │               │ │   │
│   │  │ 99.2% Acc     │  │ 5 Personas    │  │ Real-time     │ │   │
│   │  └───────────────┘  └───────────────┘  └───────────────┘ │   │
│   │                                                           │   │
│   ├───────────────────────────────────────────────────────────┤   │
│   │                                                           │   │
│   │  ┌───────────────────────┐  ┌───────────────────────────┐│   │
│   │  │ 🐍 PYTHON + FASTAPI   │  │ ☁️  GOOGLE CLOUD RUN      ││   │
│   │  │ Async, Type-safe      │  │ Serverless, Auto-scale    ││   │
│   │  └───────────────────────┘  └───────────────────────────┘│   │
│   │                                                           │   │
│   └───────────────────────────────────────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Bento Cards Content

| Card | Icon | Title | Description |
|------|------|-------|-------------|
| **Main** | 🔄 | One-Pass Architecture | "Detect, Extract, Respond—in a single API call. No round-trips." |
| **Gemini** | 🧠 | Gemini 2.5 Flash | "Google's fastest model for real-time scam classification" |
| **Detection** | 🔍 | Smart Detection | "Regex pre-filter + ML classifier = 99.2% accuracy" |
| **Personas** | 🎭 | Dynamic Personas | "5 AI personas that adapt to scammer tactics" |
| **Intel** | 💰 | Intel Extraction | "Bank accounts, UPI IDs, phishing URLs—captured automatically" |
| **Stack** | 🐍 | Python + FastAPI | "Async-first, type-safe, production-ready" |
| **Cloud** | ☁️ | Cloud Run | "Serverless deployment, scales to zero, infinite ceiling" |

### Copywriting
- **Section Label:** `THE ARCHITECTURE`
- **Headline:** "One Model. One Pass. Zero Latency."
- **Subhead:** "Traditional honeypots require multiple AI calls. Sticky-Net does detection, extraction, and response generation in a single inference—keeping scammers hooked without delay."

### Animations
1. **Flow Animation:** Data packets flow through the architecture diagram
2. **Card Hover:** Cards lift with subtle shadow on hover
3. **Stat Pulse:** Accuracy numbers pulse cyan

---

## 🖥️ Section 5: Live Demo — "The Terminal"

### Visual Concept
A **fake terminal window** styled like a hacker's console, showing a "live" log of Sticky-Net catching scammers. Features syntax highlighting and auto-scrolling text.

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   LIVE OPERATIONS                                                  │
│   ━━━━━━━━━━━━━━━━                                                │
│                                                                    │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │ ● ● ●  sticky-net@production — zsh                         │  │
│   ├────────────────────────────────────────────────────────────┤  │
│   │                                                            │  │
│   │ [10:42:15] 🕷️ STICKY-NET v2.0.0 — Production Mode         │  │
│   │ [10:42:15] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │  │
│   │                                                            │  │
│   │ [10:42:18] 📨 INCOMING: +91-98XXX-XXXXX                    │  │
│   │ [10:42:18] 📝 "Dear customer your SBI account..."          │  │
│   │ [10:42:18] 🔍 ANALYZING...                                 │  │
│   │ [10:42:19] 🚨 SCAM_DETECTED                                │  │
│   │            ├─ confidence: 0.94                             │  │
│   │            ├─ type: banking_impersonation                  │  │
│   │            └─ strategy: AGGRESSIVE                         │  │
│   │ [10:42:19] 🎭 DEPLOYING PERSONA: pushpa_verma              │  │
│   │ [10:42:20] 💬 RESPONSE: "Oh no beta! What should I do?"    │  │
│   │                                                            │  │
│   │ [10:45:33] 💰 INTEL EXTRACTED                              │  │
│   │            ├─ upi_id: scammer@ybl ████████                 │  │
│   │            ├─ bank_account: HDFC ****4521                  │  │
│   │            └─ phishing_url: bit.ly/████                    │  │
│   │                                                            │  │
│   │ [10:47:12] ⏱️ ENGAGEMENT: 00:04:54 (ongoing)               │  │
│   │ [10:47:12] 📊 SCAMMER FRUSTRATION: ████████░░ 82%          │  │
│   │                                                            │  │
│   │ [10:52:01] ✅ SESSION COMPLETE                             │  │
│   │            ├─ duration: 00:09:43                           │  │
│   │            ├─ intel_items: 3                               │  │
│   │            └─ status: SCAMMER_GAVE_UP                      │  │
│   │                                                            │  │
│   │ █                                                          │  │
│   └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│   [ Try the API → ]            [ View Full Logs → ]               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Terminal Styling
```css
.terminal {
  background: #0D1117;
  border: 1px solid #30363D;
  border-radius: 12px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  line-height: 1.6;
}

.terminal-header {
  background: #161B22;
  padding: 12px 16px;
  border-bottom: 1px solid #30363D;
}

.log-timestamp { color: #7D8590; }
.log-success { color: #4ADE80; }  /* Green */
.log-warning { color: #FFB800; }  /* Gold */
.log-error { color: #FF3366; }    /* Red */
.log-info { color: #00F5D4; }     /* Cyan */
```

### Copywriting
- **Section Label:** `LIVE OPERATIONS`
- **Headline:** "Watch the Trap in Action."
- **Subhead:** "Real logs from production (redacted for privacy). Every line is a scammer losing time."

### Animations
1. **Auto-scroll:** New log entries appear every 3-5 seconds
2. **Cursor Blink:** Terminal cursor blinks at bottom
3. **Typing Effect:** Log entries type out character by character
4. **Highlight Flash:** Intel items flash gold when extracted

---

## 📊 Section 6: Impact Metrics

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   THE IMPACT                                                       │
│   ━━━━━━━━━━━━                                                    │
│                                                                    │
│   "Every minute they spend with Pushpa is a minute                │
│    they can't spend scamming real victims."                       │
│                                                                    │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│   │            │  │            │  │            │  │            │  │
│   │   47+      │  │   2.3      │  │   156      │  │   99.2%    │  │
│   │            │  │   hours    │  │            │  │            │  │
│   │  Scammers  │  │  Wasted    │  │   UPI IDs  │  │  Detection │  │
│   │  Engaged   │  │  (theirs)  │  │  Captured  │  │  Accuracy  │  │
│   │            │  │            │  │            │  │            │  │
│   └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
│                                                                    │
│                                                                    │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │  "This is exactly the kind of innovation India needs."     │  │
│   │   — Cybersecurity Expert, CERT-In                          │  │
│   └────────────────────────────────────────────────────────────┘  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🦶 Section 7: Footer

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   ───────────────────────────────────────────────────────────────  │
│                                                                    │
│   🕷️ STICKY-NET                                                    │
│                                                                    │
│   Built with ❤️ for Google AI Hackathon 2026                       │
│                                                                    │
│   GitHub →    API Docs →    Architecture →                        │
│                                                                    │
│   ───────────────────────────────────────────────────────────────  │
│                                                                    │
│   © 2026 Team Sticky-Net. Fighting fraud, one wasted hour at a    │
│   time.                                                            │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔤 Typography

### Font Stack
```css
:root {
  /* Headlines */
  --font-display: 'Cal Sans', 'Inter', system-ui, sans-serif;
  
  /* Body */
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  
  /* Code/Terminal */
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
}
```

### Type Scale
| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Hero H1 | 72px | 700 | 1.1 |
| Section H2 | 48px | 600 | 1.2 |
| Subhead | 24px | 400 | 1.5 |
| Body | 18px | 400 | 1.6 |
| Caption | 14px | 500 | 1.4 |
| Terminal | 14px | 400 | 1.6 |

---

## ✨ Micro-Interactions

### Button Hover
```css
.btn-primary {
  background: linear-gradient(135deg, #00F5D4 0%, #00D4AA 100%);
  transition: all 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 30px rgba(0, 245, 212, 0.3);
}
```

### Card Hover
```css
.card {
  background: #111113;
  border: 1px solid #27272A;
  transition: all 0.3s ease;
}

.card:hover {
  border-color: #00F5D4;
  box-shadow: 0 0 40px rgba(0, 245, 212, 0.1);
  transform: translateY(-4px);
}
```

### Scroll Reveal
- Elements fade in + slide up on viewport entry
- Stagger delay: 100ms between elements
- Duration: 600ms
- Easing: `cubic-bezier(0.22, 1, 0.36, 1)`

---

## 📱 Responsive Breakpoints

| Breakpoint | Width | Adjustments |
|------------|-------|-------------|
| Desktop XL | 1440px+ | Full layout |
| Desktop | 1024px-1439px | Reduced padding |
| Tablet | 768px-1023px | Stack columns |
| Mobile | 320px-767px | Single column, smaller type |

---

## 🎬 Page Flow & Scrollytelling

### Scroll Sequence
1. **Hero (0-100vh):** Web animation, stats count up
2. **Problem (100-200vh):** Heatmap activates, rupee rain begins
3. **Solution (200-350vh):** Chat/Terminal split reveal
4. **Architecture (350-500vh):** Bento cards animate in
5. **Demo (500-650vh):** Terminal starts "typing"
6. **Impact (650-750vh):** Stats pulse
7. **Footer (750-800vh):** Fade in

### Scroll Indicators
- Subtle progress bar at top of viewport
- "Scroll to explore" hint fades after first scroll
- Section labels sticky at top during scroll

---

## 🎯 Key Design Principles

1. **Dark-First:** Pure blacks and deep grays, never light backgrounds
2. **Glow, Don't Shout:** Subtle neon accents, not overwhelming
3. **Data as Design:** Let the metrics and logs be visual elements
4. **Progressive Reveal:** Each scroll reveals new information
5. **Technical Credibility:** Show real code, real logs, real architecture
6. **Emotional Contrast:** Warmth of Pushpa vs. cold precision of AI

---

## 🛠️ Recommended Tech Stack for Implementation

| Tool | Purpose |
|------|---------|
| **Next.js 14** | React framework with App Router |
| **Tailwind CSS** | Utility-first styling |
| **Framer Motion** | Scroll animations |
| **GSAP ScrollTrigger** | Advanced scrollytelling |
| **Three.js / React Three Fiber** | 3D web animation (optional) |
| **Vercel** | Deployment |

---

*Design Specification v1.0 — Sticky-Net Landing Page*
*Created for Google AI Hackathon 2026*
