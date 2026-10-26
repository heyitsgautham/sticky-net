import { useEffect, useState, useRef, useCallback } from "react";
import { Send, RotateCcw, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { emptyIntel, extractionOrderFrom, mergeIntel } from "@/lib/intel";
import { loadConversations, saveConversations, generateId } from "@/lib/conversationStorage";
import { API_BASE_URL, analyzeDetailed, checkHealth } from "@/lib/api";
import { MAX_MESSAGE_CHARS, cleanMessageText } from "@/lib/limits";
import { sampleConversations } from "@/data/sampleConversations";
import { WebPattern, GlassPanel, ChatMessage } from "@/components/chat/ChatWidgets";
import { AnalysisSidebar } from "@/components/chat/AnalysisSidebar";
import { DashboardHeader } from "@/components/chat/DashboardHeader";
import { ConversationSidebar } from "@/components/chat/ConversationSidebar";

// ============ MAIN CHAT DASHBOARD ============
const ChatDashboard = () => {
    const [savedConversations, setSavedConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingConversationId, setLoadingConversationId] = useState(null);
    const [channel, setChannel] = useState("SMS");
    const [locale, setLocale] = useState("IN");
    const [metrics, setMetrics] = useState({
        scamDetected: null,
        confidence: null,
        messagesExchanged: 0,
    });
    const [extractedIntel, setExtractedIntel] = useState(emptyIntel());
    const [extractionOrder, setExtractionOrder] = useState([]);
    const [agentNotes, setAgentNotes] = useState("");
    const [connectionStatus, setConnectionStatus] = useState('unknown'); // 'connected', 'disconnected', 'unknown'

    const messagesEndRef = useRef(null);
    const messagesContainerRef = useRef(null);
    const inputRef = useRef(null);
    const currentConversationIdRef = useRef(currentConversationId);
    const extractedIntelRef = useRef(extractedIntel); // Ref to track current extractedIntel for synchronous access

    // Keep refs in sync with state
    useEffect(() => {
        currentConversationIdRef.current = currentConversationId;
    }, [currentConversationId]);

    useEffect(() => {
        extractedIntelRef.current = extractedIntel;
    }, [extractedIntel]);

    // Load saved conversations on mount
    useEffect(() => {
        const loaded = loadConversations();
        setSavedConversations(loaded);
    }, []);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (messages.length > 0 && messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "auto" });
        }
    }, [messages.length]);

    // Save current conversation to localStorage whenever it changes
    const saveCurrentConversation = useCallback(() => {
        if (!currentConversationId || messages.length === 0) return;

        const conversationData = {
            id: currentConversationId,
            title: messages[0]?.text?.substring(0, 40) + '...' || 'New Conversation',
            preview: messages[0]?.text?.substring(0, 50) || '',
            createdAt: new Date().toISOString(),
            messages,
            extractedIntel,
            extractionOrder,
            metrics,
            agentNotes,
        };

        setSavedConversations(prev => {
            const existing = prev.findIndex(c => c.id === currentConversationId);
            let updated;
            if (existing >= 0) {
                updated = [...prev];
                updated[existing] = conversationData;
            } else {
                updated = [conversationData, ...prev];
            }
            saveConversations(updated);
            return updated;
        });
    }, [currentConversationId, messages, extractedIntel, extractionOrder, metrics, agentNotes]);

    // Auto-save when messages change
    useEffect(() => {
        if (messages.length > 0 && currentConversationId) {
            saveCurrentConversation();
        }
    }, [messages, saveCurrentConversation, currentConversationId]);

    // Check backend connection
    useEffect(() => {
        checkHealth().then((ok) => setConnectionStatus(ok ? 'connected' : 'disconnected'));
    }, []);

    const handleSelectConversation = (conversation) => {
        // For sample conversations, create a read-only view (new ID to prevent saving)
        const isReadOnly = conversation.isSample;
        setCurrentConversationId(isReadOnly ? null : conversation.id);
        setMessages(conversation.messages || []);
        setMetrics(conversation.metrics || {
            scamDetected: null,
            confidence: null,
            messagesExchanged: conversation.messages?.length || 0,
        });
        setExtractedIntel(conversation.extractedIntel || emptyIntel());
        
        // Rebuild extractionOrder if it's missing but extractedIntel exists
        let order = conversation.extractionOrder || [];
        if (order.length === 0 && conversation.extractedIntel) {
            order = extractionOrderFrom(conversation.extractedIntel);
        }
        setExtractionOrder(order);
        setAgentNotes(conversation.agentNotes || "");
    };

    const handleDeleteConversation = (id) => {
        setSavedConversations(prev => {
            const updated = prev.filter(c => c.id !== id);
            saveConversations(updated);
            return updated;
        });
        if (currentConversationId === id) {
            handleNewConversation();
        }
    };

    const handleNewConversation = () => {
        const newId = generateId();
        setCurrentConversationId(newId);
        setMessages([]);
        setMetrics({
            scamDetected: null,
            confidence: null,
            messagesExchanged: 0,
        });
        const cleared = emptyIntel();
        setExtractedIntel(cleared);
        extractedIntelRef.current = cleared; // Sync ref immediately
        setExtractionOrder([]);
        setAgentNotes("");
        inputRef.current?.focus();
    };

    const handleSend = async () => {
        const text = cleanMessageText(inputValue);
        if (!text || isLoading) return;

        // Store the active conversation ID before sending
        let activeConvId = currentConversationId;

        // If viewing a sample, create a new conversation first
        const activeConversation = allConversations.find(c => c.id === activeConvId);
        if (activeConversation?.isSample || !activeConvId) {
            const newId = generateId();
            activeConvId = newId;
            setCurrentConversationId(newId);
            setMessages([]);
            setMetrics({
                scamDetected: null,
                confidence: null,
                messagesExchanged: 0,
            });
            const cleared = emptyIntel();
            setExtractedIntel(cleared);
            extractedIntelRef.current = cleared; // Sync ref immediately
            setExtractionOrder([]);
            setAgentNotes("");
        }

        const timestamp = new Date().toISOString();
        const displayTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const newMessage = {
            sender: "scammer",
            text,
            timestamp: displayTime,
            isoTimestamp: timestamp,
        };

        setMessages(prev => [...prev, newMessage]);
        setInputValue("");
        setIsLoading(true);
        setLoadingConversationId(activeConvId);

        try {
            // The detailed endpoint returns the full analysis the side panels need.
            const data = await analyzeDetailed({
                text: newMessage.text,
                timestamp,
                history: messages,
                channel,
                locale,
            });
            setConnectionStatus('connected');

            if (data.status === "success") {
                // Handle both old format (agentResponse) and new format (reply)
                const agentReplyText = data.reply || data.agentResponse;
                
                // Prepare the agent response message
                const agentMessage = agentReplyText ? {
                    sender: "agent",
                    text: agentReplyText,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    isoTimestamp: new Date().toISOString(),
                } : null;

                // Always update the conversation that sent the message, even if not currently active
                if (currentConversationIdRef.current === activeConvId) {
                    // User is still viewing the same conversation - update directly
                    if (agentMessage) {
                        setMessages(prev => [...prev, agentMessage]);
                    }

                    // Update metrics - handle both old (full response) and new (simplified) formats
                    // For simplified format, we infer scam was detected if we got a reply
                    const hasScamDetected = data.scamDetected !== undefined ? data.scamDetected : (agentReplyText ? true : null);
                    setMetrics(prev => ({
                        scamDetected: hasScamDetected ?? prev.scamDetected,
                        confidence: data.confidence ?? prev.confidence,
                        messagesExchanged: prev.messagesExchanged + (agentReplyText ? 2 : 1),
                    }));

                    // Update intel from response and track extraction order
                    // Note: Simplified API may not include extractedIntelligence
                    if (data.extractedIntelligence) {
                        const intel = data.extractedIntelligence;
                        
                        // Use the ref to get current state synchronously for comparison
                        const { updated, newExtractions } = mergeIntel(extractedIntelRef.current, intel);

                        // Update both states together - React will batch these
                        setExtractedIntel(updated);
                        extractedIntelRef.current = updated; // Sync ref immediately for next API call
                        if (newExtractions.length > 0) {
                            setExtractionOrder(prevOrder => [...prevOrder, ...newExtractions]);
                        }
                    }

                    if (data.agentNotes) {
                        setAgentNotes(data.agentNotes);
                    }
                } else {
                    // User switched to a different conversation - update saved conversations in background
                    setSavedConversations(prev => {
                        const convIndex = prev.findIndex(c => c.id === activeConvId);
                        if (convIndex >= 0 && agentMessage) {
                            const updated = [...prev];
                            const conv = updated[convIndex];
                            
                            // Handle both old (full response) and new (simplified) formats
                            const hasScamDetected = data.scamDetected !== undefined ? data.scamDetected : (agentReplyText ? true : null);
                            
                            // Add agent message to the conversation
                            updated[convIndex] = {
                                ...conv,
                                messages: [...conv.messages, agentMessage],
                                metrics: {
                                    scamDetected: hasScamDetected ?? conv.metrics?.scamDetected,
                                    confidence: data.confidence ?? conv.metrics?.confidence,
                                    messagesExchanged: (conv.messages?.length || 0) + 1,
                                },
                            };
                            
                            // Update intelligence if provided (may not be present in simplified API)
                            if (data.extractedIntelligence) {
                                const intel = data.extractedIntelligence;
                                updated[convIndex].extractedIntel = mergeIntel(conv.extractedIntel, intel).updated;
                            }
                            
                            if (data.agentNotes) {
                                updated[convIndex].agentNotes = data.agentNotes;
                            }
                            
                            saveConversations(updated);
                            return updated;
                        }
                        return prev;
                    });
                }
            }
        } catch (error) {
            console.error("API Error:", error);
            setConnectionStatus('disconnected');

            // Show error in agent notes
            setAgentNotes(`Connection error: ${error.message}. Make sure the backend is running at ${API_BASE_URL}`);
        }

        setIsLoading(false);
        setLoadingConversationId(null);
    };

    const handleReset = () => {
        handleNewConversation();
    };


    // Combine samples and saved conversations
    const allConversations = [...sampleConversations, ...savedConversations];
    
    // Check if viewing a sample conversation
    const isViewingSample = !currentConversationId && messages.length > 0;

    return (
        <div className="h-screen bg-obsidian relative overflow-hidden flex flex-col">
            <WebPattern />

            {/* Header */}
            <DashboardHeader connectionStatus={connectionStatus} />

            {/* Main Content */}
            <main className="flex-1 pt-20 px-4 md:px-6 pb-4 overflow-hidden">
                <div className="max-w-[1800px] mx-auto h-full grid grid-cols-12 gap-4 md:gap-6">

                    {/* Conversations Sidebar */}
                    <ConversationSidebar
                        savedConversations={savedConversations}
                        currentConversationId={currentConversationId}
                        onNew={handleNewConversation}
                        onSelect={handleSelectConversation}
                        onDelete={handleDeleteConversation}
                    />

                    {/* Chat Window */}
                    <div className="col-span-12 lg:col-span-6 h-full min-h-0">
                        <GlassPanel className="h-full flex flex-col min-h-0">
                            {/* Chat Header */}
                            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className={`w-3 h-3 rounded-full ${isLoading ? 'bg-yellow-400 animate-pulse' : 'bg-cyber-cyan'}`} />
                                    <h2 className="text-white font-semibold">Conversation</h2>
                                    <Badge variant="outline" className="text-gray-400 border-gray-600 text-xs">
                                        {isLoading ? 'PROCESSING' : 'MONITORING'}
                                    </Badge>
                                    {!currentConversationId && messages.length > 0 && (
                                        <Badge variant="outline" className="text-yellow-400 border-yellow-400/30 bg-yellow-400/5 text-xs">
                                            DEMO - READ ONLY
                                        </Badge>
                                    )}
                                </div>
                                {!isViewingSample && (
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={handleReset}
                                        className="bg-cyber-red/20 text-cyber-red border border-cyber-red/30 hover:bg-cyber-red/30"
                                    >
                                        <RotateCcw className="w-4 h-4 mr-2" />
                                        Reset
                                    </Button>
                                )}
                            </div>

                            {/* Messages Area */}
                            <div 
                                ref={messagesContainerRef}
                                className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 md:p-6"
                                style={{ scrollbarWidth: 'thin' }}
                            >
                                {messages.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-gray-500">
                                        <MessageSquare className="w-16 h-16 mb-4 opacity-30" />
                                        <p className="text-center font-mono text-sm">
                                            Start a conversation by typing a scam message below.
                                        </p>
                                        <p className="text-center text-xs mt-2 text-gray-600">
                                            Example: &quot;Your bank account has been compromised. Send OTP to verify.&quot;
                                        </p>
                                        {connectionStatus === 'disconnected' && (
                                            <p className="text-center text-xs mt-4 text-red-400">
                                                ⚠️ Backend not connected. Start the server at {API_BASE_URL}
                                            </p>
                                        )}
                                    </div>
                                ) : (
                                    <>
                                        {messages.map((msg, idx) => (
                                            <ChatMessage
                                                key={`msg-${idx}`}
                                                message={msg}
                                                isAgent={msg.sender === "agent"}
                                            />
                                        ))}
                                    </>
                                )}
                                {isLoading && loadingConversationId === currentConversationId && (
                                    <div className="flex justify-end mb-4">
                                        <div className="bg-cyber-cyan/20 border border-cyber-cyan/30 rounded-2xl rounded-br-sm px-4 py-3">
                                            <div className="flex gap-1">
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                                <span className="w-2 h-2 bg-cyber-cyan rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                            </div>
                                        </div>
                                    </div>
                                )}
                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input Area */}
                            <div className="p-4 border-t border-white/10 flex-shrink-0">
                                {isViewingSample ? (
                                    <div className="text-center py-4">
                                        <p className="text-gray-500 text-sm font-mono">
                                            📖 This is a demo example. Click &quot;New&quot; to start your own conversation.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex gap-3 items-end">
                                        <textarea
                                            ref={inputRef}
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            onPaste={() => {
                                                // Let default paste behavior work, then trigger resize
                                                setTimeout(() => {
                                                    if (inputRef.current) {
                                                        inputRef.current.style.height = 'auto';
                                                        inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 200) + 'px';
                                                    }
                                                }, 0);
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault();
                                                    handleSend();
                                                }
                                            }}
                                            maxLength={MAX_MESSAGE_CHARS}
                                            placeholder="Type scammer message... (Shift+Enter for new line)"
                                            rows={3}
                                            className="
                      flex-1 bg-black border border-white/20 rounded-xl px-4 py-3
                      font-mono text-sm text-gray-200 placeholder:text-gray-600
                      focus:outline-none focus:border-cyber-cyan focus:shadow-cyan-glow
                      transition-all duration-300 resize-none overflow-y-auto scrollbar-thin
                      min-h-[80px] max-h-[200px]
                    "
                                            style={{
                                                height: 'auto',
                                                lineHeight: '1.5rem',
                                                whiteSpace: 'pre-wrap',
                                                wordWrap: 'break-word',
                                                overflowWrap: 'break-word'
                                            }}
                                            onInput={(e) => {
                                                e.target.style.height = 'auto';
                                                e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
                                            }}
                                        />
                                        <Button
                                            onClick={handleSend}
                                            disabled={isLoading || !inputValue.trim()}
                                            className="
                      bg-cyber-cyan text-black font-mono font-bold px-6
                      hover:bg-cyber-cyan/80 disabled:opacity-50
                      shadow-cyan-glow transition-all duration-300 h-[44px]
                    "
                                        >
                                            <Send className="w-4 h-4 mr-2" />
                                            Send
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </GlassPanel>
                    </div>

                    {/* Right Sidebar - Metrics & Intel */}
                    <AnalysisSidebar
                        channel={channel}
                        setChannel={setChannel}
                        locale={locale}
                        setLocale={setLocale}
                        metrics={metrics}
                        extractionOrder={extractionOrder}
                        agentNotes={agentNotes}
                    />
                </div>
            </main>
        </div>
    );
};

export default ChatDashboard;
