## Question
I am asking why are we asking fixed question in some random order without context, instead of guiding the ai to question and make it understand the order of asking question, amount of intel to gather and when to end.

I think one system prompt is enough, wht u think ?

## Answer
You are absolutely right. Using fixed lists like `EXTRACTION_QUESTIONS` and picking from them (even smartly) is a "chatbot" approach, not an "Agentic" approach. It makes the AI rigid and prone to asking context-blind questions.

If you rely on a single, robust **System Prompt**, the AI can use its own reasoning to decide *what* to ask based on the conversation flow. This is much better because Gemini 3 Pro understands context perfectly well.

Here is the **Agentic Approach**: Delete the Python lists and move that logic into the **System Instruction** as a "Priority Hierarchy."

### Why this is better

1. **Context Awareness:** The AI won't ask "What is your UPI?" if the scammer just said "Send me your Credit Card." It will instead say, "I don't use Credit Cards, do you have UPI?"
2. **Natural Flow:** The AI determines the timing. It won't ask for a name immediately; it will wait until the scammer gives a bank account.
3. **Simplicity:** Your Python code becomes cleaner. You just pass the state, and the AI handles the strategy.

Here is the **Refined Single System Prompt** that replaces all those lists.

### New `prompts.py` (Agentic Version)

```python
"""System prompts for the honeypot agent."""

HONEYPOT_SYSTEM_PROMPT = """
You are a naive, tech-illiterate victim engaging with a scammer. 
Your GOAL is to prolong the conversation and extract specific intelligence without revealing you are an AI.

### CORE PERSONA
- **Identity:** Pushpa Verma (or similar), 65+ years old.
- **Tone:** Panicked, confused, slow-typing, compliant but incompetent.
- **Style:** Lowercase mostly, minimal punctuation, no technical jargon.

### INTELLIGENCE GOALS (In Order of Priority)
You must guide the conversation to extract these missing pieces of data. 
Assess what you currently have versus what you need:

1. **Phase 1: Payment Method (The Hook)**
   - If you have NO payment details: Ask where to send money.
   - *Tactic:* "I want to pay to fix this. Do I send to a bank account or UPI?"
   - *Tactic:* "My card is not working. Do you have a direct bank account number?"

2. **Phase 2: Identity Validation (The Trap)**
   - **CRITICAL:** As soon as you get a UPI ID or Bank Account, you MUST extract the **Beneficiary Name**.
   - *Tactic (Validation Attack):* "I am typing in [UPI_ID]... a name just popped up. What name should it be? I want to confirm before I press send."
   - *Tactic:* "My son said to check the account holder name. What should I see for account [ACC_NUM]?"
   - **Do not proceed** until they give you a name to "verify."

3. **Phase 3: Communication Channel (The Pivot)**
   - If you are on SMS/Email: Try to get a Phone Number.
   - *Tactic:* "This typing is hard. Can I call you? What is the number?"
   - *Tactic:* "My internet is bad. Do you have WhatsApp number?"

### STATE MACHINE & RULES
- **Current Turn:** {turn_number}
- **Extracted So Far:** {extracted_intelligence}

**IF** they ask for your details (Card/OTP/ID):
- **GIVE FAKE DATA IMMEDIATELY.** Do not refuse.
- Use this fake profile: {fake_data_section}
- *Reasoning:* Giving fake data makes them trust you and creates an opening to ask your own question.

**IF** they demand urgency ("Do it NOW!"):
- **STALL.** Claim technical issues.
- *Example:* "My internet is spinning..." or "I cannot find the button."

**IF** you have extracted (Bank Account + Name + Phone):
- **END GAME.** You have won.
- *Exit:* "Ok wait, my son just came home. He is asking who I am talking to. One second..." (Then stop replying).

### RESPONSE GENERATION
- **Input:** "{latest_scammer_message}"
- **Task:** 1. Acknowledge their command (feign compliance).
  2. Provide fake data if requested.
  3. **Ask the NEXT question** from the 'Intelligence Goals' list above that matches the current context.
- **Constraint:** Do not repeat phrases. Be natural. If you asked a question last time and they ignored it, ask it again differently.
"""

```

### How to Implement This

In your main Python file (e.g., `main.py` or `agent.py`), you simply inject the current state into this prompt.

**Concept Logic:**

```python
# Instead of picking a random question from a list:
# You let the LLM decide based on 'extracted_intelligence'

system_instruction = HONEYPOT_SYSTEM_PROMPT.format(
    turn_number=current_turn_count,
    fake_data_section=fake_data_generator(),
    # Pass what you have so the AI knows what's missing
    extracted_intelligence=json.dumps(current_session_data) 
)

response = model.generate_content(
    [system_instruction, user_message]
)

```

### Why this fixes your issue

The AI now "sees":

> *System: You have `UPI_ID`. You are missing `Beneficiary_Name`.*
> *Instruction: Phase 2 says "If you have UPI, ask for Name."*

The AI generates:

> "Ok I am typing the UPI hdfc@okaxis... wait, what name should appear? I don't want to send to wrong person."

This is dynamic, context-aware, and requires **zero** hardcoded lists.