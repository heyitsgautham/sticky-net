## Question
Conversation:
AMAZON ALERT: Your account has been charged ₹24,999 for an iPhone 13 order (Order #AMZ-9988). We noticed suspicious activity. If this order was not placed by you, reply 'NO' immediately to cancel. Call our Fraud Department Support at +91-88888-99999 for an instant refund.
01:05 PM
🤖 Honeypot Agent
please help me understand no i did not order this. waht is this. 25000 is a lot
01:05 PM
👤 Scammer
Okay, thank you for confirming. We have put a temporary hold on the transaction. To process your Full Refund of ₹24,999 back to your bank account, you must fill out the Cancellation Form immediately. Click here: http://amazon-refund-support-quick.com/cancel-order Do not delay! The hold expires in 10 minutes. Tell me once you open the link.
01:06 PM
🤖 Honeypot Agent
what do i do ok beta i am very scared. i dont know how to do this form thing. is there no
01:06 PM

Before we continue further there are few things we need to address

"What do i do" starting is a hardcoded thing.

persona.py
"""Human persona management for the honeypot agent."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PersonaTrait(str, Enum):
    """Persona personality traits."""

    TRUSTING = "trusting"
    WORRIED = "worried"
    CONFUSED = "confused"
    COOPERATIVE = "cooperative"
    TECH_NAIVE = "tech_naive"


class EmotionalState(str, Enum):
    """Current emotional state of the persona."""

    CALM = "calm"
    ANXIOUS = "anxious"
    PANICKED = "panicked"
    RELIEVED = "relieved"
    SUSPICIOUS = "suspicious"  # Use sparingly, only late in conversation
    # Context-aware states based on scam type
    INTERESTED = "interested"  # For job offers - curious about opportunity
    EXCITED = "excited"  # For lottery/rewards - happy about winning
    CAUTIOUS = "cautious"  # For impersonation - intimidated but careful
    NEUTRAL = "neutral"  # For unknown scam types - no strong emotion


@dataclass
class Persona:
    """Represents the honeypot's human persona."""

    traits: list[PersonaTrait] = field(default_factory=lambda: [
        PersonaTrait.TRUSTING,
        PersonaTrait.WORRIED,
        PersonaTrait.TECH_NAIVE,
    ])
    emotional_state: EmotionalState = EmotionalState.CALM
    engagement_turn: int = 0

    # Conversation memory
    claimed_issues: list[str] = field(default_factory=list)
    mentioned_details: dict[str, Any] = field(default_factory=dict)

    def update_emotional_state(self, scam_intensity: float, scam_type: str | None = None) -> None:
        """
        Update emotional state based on scam type and intensity.
        
        Different scam types evoke different emotional responses:
        - job_offer: Interest/curiosity (excited about opportunity)
        - banking_fraud: Panic/anxiety (scared about account)
        - lottery_reward: Excitement (happy about winning)
        - impersonation: Caution/nervousness (intimidated by authority)
        - others/None: Neutral/calm (confused, no strong emotion)
        """
        # Map scam types to appropriate emotions
        scam_type_emotions = {
            "job_offer": (EmotionalState.INTERESTED, EmotionalState.INTERESTED),  # (high, low)
            "banking_fraud": (EmotionalState.PANICKED, EmotionalState.ANXIOUS),
            "lottery_reward": (EmotionalState.EXCITED, EmotionalState.EXCITED),
            "impersonation": (EmotionalState.CAUTIOUS, EmotionalState.CAUTIOUS),
            "others": (EmotionalState.NEUTRAL, EmotionalState.CALM),
        }
        
        # Get emotions for this scam type, default to neutral/calm for unknown types
        high_emotion, low_emotion = scam_type_emotions.get(
            scam_type, (EmotionalState.NEUTRAL, EmotionalState.CALM)
        )
        
        # Use intensity to determine which emotion variant
        if scam_intensity > 0.6:
            self.emotional_state = high_emotion
        else:
            self.emotional_state = low_emotion

    def get_emotional_modifier(self) -> str:
        """
        Get text modifier based on emotional state.
        
        Returns varied modifiers to avoid repetition - picks randomly
        from options appropriate to the emotional state.
        """
        modifiers = {
            EmotionalState.CALM: [
                "",
                "ok so ",
                "let me understand ",
                "hmm ",
            ],
            EmotionalState.ANXIOUS: [
                "this is worrying me ",
                "i am concerned now ",
                "wait what ",
                "this doesnt sound right ",
                "one second ",
            ],
            EmotionalState.PANICKED: [
                "ok ok i am scared ",
                "please help me understand ",
                "my hands are shaking ",
                "what do i do ",
                "i dont want trouble ",
            ],
            EmotionalState.RELIEVED: [
                "ok good ",
                "alright then ",
                "that makes sense ",
            ],
            EmotionalState.SUSPICIOUS: [
                "wait ",
                "hold on ",
                "but ",
                "i am not sure ",
            ],
            # New context-aware emotional states
            EmotionalState.INTERESTED: [
                "oh that sounds nice ",
                "tell me more ",
                "i am interested ",
                "this sounds like a good opportunity ",
                "really ",
            ],
            EmotionalState.EXCITED: [
                "oh wow really ",
                "that is great news ",
                "i cant believe it ",
                "this is amazing ",
                "oh my god ",
            ],
            EmotionalState.CAUTIOUS: [
                "hmm i see ",
                "let me think ",
                "are you sure ",
                "ok ok ",
                "i understand sir ",
            ],
            EmotionalState.NEUTRAL: [
                "",
                "ok ",
                "i see ",
                "alright ",
                "mmm ",
            ],
        }
        options = modifiers.get(self.emotional_state, [""])
        return random.choice(options)

    def increment_turn(self) -> None:
        """Increment the engagement turn counter."""
        self.engagement_turn += 1


class PersonaManager:
    """Manages persona state across conversation turns."""

    def __init__(self) -> None:
        """Initialize persona manager."""
        self.personas: dict[str, Persona] = {}

    def get_or_create_persona(self, conversation_id: str) -> Persona:
        """Get existing persona or create new one for a conversation."""
        if conversation_id not in self.personas:
            self.personas[conversation_id] = Persona()
        return self.personas[conversation_id]

    def update_persona(
        self,
        conversation_id: str,
        scam_intensity: float,
        scam_type: str | None = None,
    ) -> Persona:
        """Update persona state after a turn."""
        persona = self.get_or_create_persona(conversation_id)
        persona.increment_turn()
        persona.update_emotional_state(scam_intensity, scam_type)
        return persona

    def get_turn_guidance(self, turn: int) -> str:
        """
        Get guidance for response style based on turn number.
        
        This helps vary the persona's behavior across the conversation
        to avoid repetitive patterns.
        """
        if turn <= 2:
            return (
                "You are confused and asking basic questions. "
                "Use phrases like 'i dont understand', 'what is this about', 'who is this'."
            )
        elif turn <= 5:
            return (
                "You are worried but trying to understand. "
                "Use phrases like 'this is concerning', 'what should i do', 'is this serious'."
            )
        elif turn <= 10:
            return (
                "You are compliant but slow. "
                "Use phrases like 'ok let me try', 'wait i need to find my glasses', 'how do i do this'."
            )
        else:
            return (
                "You are cooperative but hesitant about money. "
                "Use phrases like 'that is a lot of money', 'let me check my balance', 'my son handles this usually'."
            )

    def get_persona_context(self, conversation_id: str) -> dict[str, Any]:
        """Get persona context for prompt injection."""
        persona = self.get_or_create_persona(conversation_id)
        turn = persona.engagement_turn
        return {
            "emotional_state": persona.emotional_state.value,
            "engagement_turn": turn,
            "emotional_modifier": persona.get_emotional_modifier(),
            "turn_guidance": self.get_turn_guidance(turn),
        }

    def clear_persona(self, conversation_id: str) -> None:
        """Clear persona for a completed conversation."""
        self.personas.pop(conversation_id, None)


Is this file also needs change by removing hardcoding and make the agentic ai handle it.
Also we need to remove all the hardcoding right, if so let's do it, tell me what to ask my ai coding assistant to understand the rest of the hardcoding, because the phone number also not extracted as regex only search if it does not have hypen, adding that regex does not solve as many like this will arise, we should make the agentic ai extract the phone number and other details and also provide the agentic ai the ability to add extra fields to the extracted info if some useful information is extracted but it is not the regular upi id, phising link, number, name or bank account but not too much ability that it extracts useless things like order id

What is your honest opinion on my takes, which all you think are correct and which all you think wrong ? 


## Answer
Here is my honest assessment of your takes.

### **1. Your Take: "`persona.py` hardcoding is bad."**

**Verdict: 100% Correct.**
You identified the exact root cause of the robotic behavior.

* **The Problem:** The `get_emotional_modifier()` method (Lines 66-124) forces specific strings like *"what do i do"* or *"ok ok i am scared"* onto the start of every message.
* **Why it fails:** It overrides the LLM's natural language generation. Even if the LLM writes a great response, your Python code accidentally makes it sound repetitive by pasting the same 3 phrases on top.
* **The Fix:** Delete these string dictionaries. Pass the **Emotional State** (e.g., `PANICKED`) to the *System Prompt*, and let the LLM decide how to express panic.

### **2. Your Take: "Regex extraction is brittle."**

**Verdict: 100% Correct.**

* **The Problem:** Your regex failed to catch `+91-88888-99999` because it probably didn't account for hyphens. You will fight a losing battle trying to write regex for every possible phone number format (spaces, dots, brackets).
* **The Fix:** LLMs are excellent at this. They understand context. An LLM knows that *"Call 9988-7766"* is a phone number even if the formatting is weird.

### **3. Your Take: "Allow Agentic AI to extract extra fields (smartly)."**

**Verdict: Correct, with a warning.**

* **The Goal:** You want to catch things you didn't plan for, like "Bitcoin Wallet Address" or "TeamViewer ID".
* **The Risk:** If you make it too open, the AI might extract useless things like "Order Number" or "Sender Name: Amazon".
* **The Fix:** We will use a **"One-Pass" Architecture**. We won't have a separate `extractor.py` anymore. The main Engagement Agent will return a JSON object containing both the **Reply** and the **Extracted Data**.

---

### **Action Plan: The "Agentic Refactor"**

We are going to delete about 60% of your Python code and move that logic into the System Prompt. This makes the system smarter and easier to maintain.

**Here is the prompt to give to your AI Coding Assistant.** It covers removing the hardcoding in `persona.py`, deleting the regex extractor, and implementing the new JSON-based agent.

---

### **Prompt for Your AI Coding Assistant**

```text
@workspace I need to refactor the Sticky-Net agent to be fully "Agentic" and remove brittle hardcoding. 

Here are the specific architectural changes I need:

### 1. Refactor `persona.py` (Remove Hardcoded Strings)
- Keep the `Persona` class and `EmotionalState` enum for state tracking.
- **DELETE** the `get_emotional_modifier()` method entirely. We will not prepend strings like "what do i do" anymore.
- **DELETE** the `get_turn_guidance()` method. 
- The `Persona` class should only be a simple data container that tracks `engagement_turn`, `emotional_state`, and `scam_type`.

### 2. Delete `extractor.py` (Remove Regex)
- We are abandoning regex-based extraction. It is too brittle.
- Delete the `extractor.py` file or deprecate its usage in the main pipeline.

### 3. Update `honeypot_agent.py` (One-Pass JSON Architecture)
- Modify the main LLM call to return **Structured JSON** instead of plain text.
- The Agent should generate the Reply and the Extracted Intelligence in a single API call.
- **Output Schema:**
  ```json
  {
    "reply_text": "The message to send back to the scammer",
    "emotional_tone": "The emotion used (e.g., panicked, compliant)",
    "extracted_intelligence": {
      "phone_numbers": ["extract valid phone numbers"],
      "upi_ids": ["extract UPIs"],
      "bank_accounts": ["extract account numbers"],
      "urls": ["extract phishing links"],
      "beneficiary_names": ["extract names associated with payments"],
      "other_critical_info": [
        {"label": "Wallet Address", "value": "..."},
        {"label": "App Download", "value": "AnyDesk"}
      ]
    },
    "scam_analysis": {
        "scam_type": "job/bank/refund",
        "missing_critical_intel": ["beneficiary_name", "phone"] 
    }
  }

```

### 4. Update `prompts.py` (The Brain)

* Update the `HONEYPOT_SYSTEM_PROMPT` to enforce this JSON output.
* **Instruction for Intelligence:** "Analyze the incoming message for ANY contact details or payment info. Extract them into the JSON. If you find high-value intel that doesn't fit standard fields (like Crypto addresses or Remote Desktop IDs), add them to 'other_critical_info'. Do NOT extract generic info like Order IDs or Company Names."
* **Instruction for Persona:** "Adopt the persona based on the provided state. Do NOT use repetitive prefixes. Weave the emotion into the text naturally."

### 5. Update `policy.py` / `main.py`

* Update the logic to parse this JSON response.
* Save the extracted intelligence directly to the database/logs.
* Send `reply_text` to the user.

Please implement these changes now.

