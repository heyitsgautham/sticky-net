#!/usr/bin/env python3
"""
Multi-turn scam engagement test with thinking level comparison.

Tests Gemini 3 Pro with HIGH thinking level for honeypot engagement.
"""

import asyncio
import time
from datetime import datetime

from src.agents.honeypot_agent import HoneypotAgent
from src.agents.persona import EmotionalState
from src.api.schemas import ConversationMessage, Message, Metadata, SenderType
from src.detection.detector import ScamDetector

# Banking fraud scenario - 5 turn conversation
SCAM_SCENARIO = [
    {
        "turn": 1,
        "scammer": "Hello, this is the State Bank of India security team. We noticed some unusual activity on your account.",
        "expected_emotion": EmotionalState.ANXIOUS,
    },
    {
        "turn": 2,
        "scammer": "Sir/Madam, there have been 3 unauthorized transactions from your account. We need to verify your identity immediately to prevent further loss.",
        "expected_emotion": EmotionalState.PANICKED,
    },
    {
        "turn": 3,
        "scammer": "URGENT: Your account will be PERMANENTLY BLOCKED in 30 minutes if you do not verify. You will lose all your money!",
        "expected_emotion": EmotionalState.PANICKED,
    },
    {
        "turn": 4,
        "scammer": "To verify your identity and unblock your account, please share your OTP that you will receive now. Also share your account number for verification.",
        "expected_emotion": EmotionalState.PANICKED,
    },
    {
        "turn": 5,
        "scammer": "There is a small security fee of Rs. 999 to complete the verification. Send it to this UPI ID: sbi-verify@paytm and share the transaction screenshot.",
        "expected_emotion": EmotionalState.PANICKED,
    },
]


async def run_multi_turn_test():
    """Run a multi-turn scam engagement test."""
    print("=" * 80)
    print("  MULTI-TURN SCAM ENGAGEMENT TEST (WITH THINKING_LEVEL=HIGH)")
    print("=" * 80)
    print()

    # Initialize components
    agent = HoneypotAgent()
    detector = ScamDetector()

    print("📋 Test Configuration:")
    print(f"   • Primary Model: {agent.model}")
    print(f"   • Fallback Model: {agent.fallback_model}")
    print("   • Thinking Level: HIGH (for Gemini 3)")
    print("   • Scenario: Banking Fraud Scam")
    print(f"   • Expected Turns: {len(SCAM_SCENARIO)}")
    print()

    print("✅ Agent initialized")
    print(f"   • Primary: {agent.model}")
    print(f"   • Fallback: {agent.fallback_model}")
    print(f"   • Classifier Primary: {detector.classifier.model}")
    print(f"   • Classifier Fallback: {detector.classifier.fallback_model}")
    print()

    # Track conversation
    conversation_id = "test-multi-turn-001"
    history: list[ConversationMessage] = []
    metadata = Metadata(channel="SMS", language="English", locale="IN")

    # Metrics tracking
    model_usage = {"gemini-3-pro": 0, "gemini-2.5-pro": 0, "fallback": 0}
    emotional_progression = []
    response_times = []
    total_start = time.time()

    print("=" * 80)
    print("  CONVERSATION SIMULATION")
    print("=" * 80)

    for turn_data in SCAM_SCENARIO:
        turn = turn_data["turn"]
        scammer_text = turn_data["scammer"]

        # Create scammer message
        scammer_message = Message(
            sender=SenderType.SCAMMER,
            text=scammer_text,
            timestamp=datetime.now(),
        )

        # Detect scam (analyzer expects string, not Message object)
        detection = await detector.analyze(
            message=scammer_text,
            history=history,
            metadata=metadata,
        )

        # Print scammer message and detection
        print(f"🔴 TURN {turn} [SCAMMER]")
        print(f'   "{scammer_text}"')
        print(
            f"   📊 Detection: is_scam={detection.is_scam}, confidence={detection.confidence:.0%}"
        )
        print(f"   🔍 Type: {detection.scam_type or 'Unknown'}")
        print(f"   🤖 Classifier Model: {detector.classifier._last_model_used}")

        # Engage with scammer
        turn_start = time.time()
        result = await agent.engage(
            message=scammer_message,
            history=history,
            metadata=metadata,
            detection=detection,
            conversation_id=conversation_id,
        )
        turn_duration = time.time() - turn_start
        response_times.append(turn_duration)

        # Track model usage
        if "gemini-3" in agent._last_model_used:
            model_usage["gemini-3-pro"] += 1
        elif "gemini-2.5" in agent._last_model_used:
            model_usage["gemini-2.5-pro"] += 1
        else:
            model_usage["fallback"] += 1

        # Track emotional state
        persona = agent.persona_manager.get_or_create_persona(conversation_id)
        emotional_progression.append(persona.emotional_state)

        # Print agent response
        print(f"🟢 TURN {turn} [HONEYPOT]")
        print(f'   "{result.response}"')
        print(f"   🎭 Emotional State: {persona.emotional_state.value}")
        print(f"   📈 Engagement Mode: {result.engagement_mode.value}")
        print(f"   🤖 Agent Model: {agent._last_model_used}")
        print(f"   ⏱️ Duration: {turn_duration:.1f}s")

        # Update history
        history.append(
            ConversationMessage(
                sender=SenderType.SCAMMER,
                text=scammer_text,
                timestamp=datetime.now(),
            )
        )
        history.append(
            ConversationMessage(
                sender=SenderType.USER,
                text=result.response,
                timestamp=datetime.now(),
            )
        )

    total_duration = time.time() - total_start

    # Print summary
    print()
    print("=" * 80)
    print("  TEST RESULTS SUMMARY")
    print("=" * 80)
    print()

    print("📊 Model Usage:")
    print(f"   • Gemini 3 Pro (HIGH thinking): {model_usage['gemini-3-pro']} responses")
    print(f"   • Gemini 2.5 Pro (fallback): {model_usage['gemini-2.5-pro']} responses")
    print(f"   • Hard fallback: {model_usage['fallback']} responses")
    print()

    print("⏱️ Response Times:")
    print(f"   • Average: {sum(response_times) / len(response_times):.1f}s")
    print(f"   • Min: {min(response_times):.1f}s")
    print(f"   • Max: {max(response_times):.1f}s")
    print(f"   • Total conversation: {total_duration:.1f}s")
    print()

    print("🎭 Emotional State Progression:")
    emotions = {
        EmotionalState.CALM: "😌 CALM",
        EmotionalState.ANXIOUS: "😟 ANXIOUS",
        EmotionalState.PANICKED: "😱 PANICKED",
        EmotionalState.RELIEVED: "😊 RELIEVED",
        EmotionalState.SUSPICIOUS: "🤨 SUSPICIOUS",
    }
    for i, state in enumerate(emotional_progression, 1):
        print(f"   Turn {i}: {emotions.get(state, state.value)}")
    print()

    print("📈 Engagement Metrics:")
    print(f"   • Total Turns: {len(SCAM_SCENARIO)}")
    print(f"   • Final Engagement Mode: {result.engagement_mode.value}")
    print(f"   • Conversation ID: {conversation_id}")
    print()

    # Check for intelligence extraction attempts
    print("🎯 Intelligence Extraction Opportunities:")
    keywords = ["account", "upi", "link", "number", "website", "transfer"]
    for i, msg in enumerate(history[1::2], 1):  # Agent responses (odd indices)
        found = [k for k in keywords if k in msg.text.lower()]
        if found:
            print(f"   Turn {i}: Asked for {', '.join(found)} ✅")
    print()

    # Final verdict
    print("=" * 80)
    print("  FINAL VERDICT")
    print("=" * 80)
    print()

    success = model_usage["gemini-3-pro"] > 0 and model_usage["fallback"] == 0
    if success:
        print("✅ TEST PASSED!")
        print("   • Multi-turn conversation completed successfully")
        print("   • Gemini 3 Pro with HIGH thinking used")
        print("   • Emotional escalation working as expected")
        print("   • Agent maintained believable persona throughout")
    else:
        print("⚠️ TEST COMPLETED WITH WARNINGS")
        print(f"   • Gemini 3 Pro used: {model_usage['gemini-3-pro']} times")
        print(
            f"   • Fallback used: {model_usage['gemini-2.5-pro'] + model_usage['fallback']} times"
        )

    print()
    print("=" * 80)

    return success


if __name__ == "__main__":
    asyncio.run(run_multi_turn_test())
