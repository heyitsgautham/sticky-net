// State management
let conversationHistory = [];
let startTime = null;
let isProcessing = false;

// DOM elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const statusBadge = document.getElementById('statusBadge');

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function formatTimestamp(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
    });
}

function addMessage(sender, text, isAgent = false) {
    // Remove empty state if present
    const emptyState = chatMessages.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isAgent ? 'agent' : 'scammer'}`;
    messageDiv.innerHTML = `
        <div class="sender">${isAgent ? '🤖 Honeypot Agent' : '👤 Scammer'}</div>
        <div class="text">${escapeHtml(text)}</div>
        <div class="timestamp">${formatTimestamp(new Date())}</div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showThinking() {
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'thinking-indicator';
    thinkingDiv.id = 'thinkingIndicator';
    thinkingDiv.innerHTML = `
        <div class="thinking-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <span style="font-size: 0.85rem; color: var(--text-muted);">Analyzing...</span>
    `;
    chatMessages.appendChild(thinkingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideThinking() {
    const thinking = document.getElementById('thinkingIndicator');
    if (thinking) thinking.remove();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateMetrics(response) {
    // Scam detected
    const scamDetected = document.getElementById('scamDetected');
    scamDetected.textContent = response.scamDetected ? 'Yes' : 'No';
    scamDetected.className = `metric-value ${response.scamDetected ? 'danger' : 'success'}`;

    // Status badge
    if (response.scamDetected) {
        statusBadge.textContent = 'Scam Detected';
        statusBadge.className = 'status-badge scam';
    }

    // Messages count
    document.getElementById('messagesCount').textContent = 
        response.engagementMetrics?.totalMessagesExchanged || conversationHistory.length;

    // Duration
    if (startTime) {
        const duration = Math.round((Date.now() - startTime) / 1000);
        document.getElementById('duration').textContent = `${duration}s`;
    }

    // Confidence (estimate based on scam detection)
    const confidenceValue = response.confidence ?? (response.scamDetected ? 0.85 : 0.15);
    const confidence = document.getElementById('confidence');
    confidence.textContent = `${Math.round(confidenceValue * 100)}%`;
    confidence.className = `metric-value ${confidenceValue > 0.6 ? 'danger' : 'success'}`;

    // Confidence bar
    const confidenceBar = document.getElementById('confidenceBar');
    confidenceBar.style.width = `${confidenceValue * 100}%`;
    confidenceBar.style.background = confidenceValue > 0.85 ? 'var(--danger)' : 
                                     confidenceValue > 0.6 ? 'var(--warning)' : 
                                     'var(--success)';

    // Agent notes
    document.getElementById('agentNotes').textContent = response.agentNotes || '-';
}

function updateIntelligence(intelligence) {
    const content = document.getElementById('intelligenceContent');

    // DEBUG: Log received intelligence
    console.log('updateIntelligence called with:', intelligence);
    console.log('Intelligence type:', typeof intelligence);
    console.log('Has bankAccounts?', intelligence?.bankAccounts);
    console.log('Has upiIds?', intelligence?.upiIds);

    // Check if any intelligence exists
    const hasIntel = intelligence && (
        intelligence.bankAccounts?.length ||
        intelligence.upiIds?.length ||
        intelligence.phishingLinks?.length ||
        intelligence.phoneNumbers?.length ||
        intelligence.emailAddresses?.length ||
        intelligence.beneficiaryNames?.length ||
        intelligence.whatsappNumbers?.length ||
        intelligence.ifscCodes?.length ||
        intelligence.cryptoAddresses?.length ||
        intelligence.other_critical_info?.length
    );

    if (!hasIntel) {
        content.innerHTML = '<div class="empty-state"><p>No intelligence extracted yet.</p></div>';
        return;
    }

    let html = '';

    if (intelligence.bankAccounts?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">🏦 Bank Accounts</div>
                <ul class="intel-list">
                    ${intelligence.bankAccounts.map(acc => 
                        `<li class="intel-item">${escapeHtml(acc)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.upiIds?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">📱 UPI IDs</div>
                <ul class="intel-list">
                    ${intelligence.upiIds.map(upi => 
                        `<li class="intel-item">${escapeHtml(upi)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.emailAddresses?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">📧 Email Addresses</div>
                <ul class="intel-list">
                    ${intelligence.emailAddresses.map(email => 
                        `<li class="intel-item">${escapeHtml(email)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.phoneNumbers?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">📞 Phone Numbers</div>
                <ul class="intel-list">
                    ${intelligence.phoneNumbers.map(phone => 
                        `<li class="intel-item">${escapeHtml(phone)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.whatsappNumbers?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">💬 WhatsApp Numbers</div>
                <ul class="intel-list">
                    ${intelligence.whatsappNumbers.map(wa => 
                        `<li class="intel-item">${escapeHtml(wa)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.beneficiaryNames?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">👤 Beneficiary Names</div>
                <ul class="intel-list">
                    ${intelligence.beneficiaryNames.map(name => 
                        `<li class="intel-item">${escapeHtml(name)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.ifscCodes?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">🏛️ IFSC Codes</div>
                <ul class="intel-list">
                    ${intelligence.ifscCodes.map(code => 
                        `<li class="intel-item">${escapeHtml(code)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.phishingLinks?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">🔗 Phishing Links</div>
                <ul class="intel-list">
                    ${intelligence.phishingLinks.map(link => 
                        `<li class="intel-item">${escapeHtml(link)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.cryptoAddresses?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">🪙 Crypto Addresses</div>
                <ul class="intel-list">
                    ${intelligence.cryptoAddresses.map(addr => 
                        `<li class="intel-item">${escapeHtml(addr)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (intelligence.other_critical_info?.length) {
        html += `
            <div class="intel-section">
                <div class="intel-category">📋 Other Critical Info</div>
                <ul class="intel-list">
                    ${intelligence.other_critical_info.map(item => 
                        `<li class="intel-item"><strong>${escapeHtml(item.label)}:</strong> ${escapeHtml(item.value)}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    content.innerHTML = html;
}

async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isProcessing) return;

    // Start timer on first message
    if (!startTime) startTime = Date.now();

    isProcessing = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="loading"></span>';

    // Add scammer message to UI
    addMessage('scammer', text);
    messageInput.value = '';

    // Show thinking indicator
    showThinking();

    // Prepare request
    const timestamp = new Date().toISOString();
    const request = {
        message: {
            sender: 'scammer',
            text: text,
            timestamp: timestamp
        },
        conversationHistory: conversationHistory.map(msg => ({
            sender: msg.sender,
            text: msg.text,
            timestamp: msg.timestamp
        })),
        metadata: {
            channel: document.getElementById('channelSelect').value,
            language: 'English',
            locale: document.getElementById('localeSelect').value
        }
    };

    try {
        // Send a key only when one is typed; a DEBUG=true server accepts none.
        const apiKey = document.getElementById('apiKeyInput').value.trim();
        const headers = { 'Content-Type': 'application/json' };
        if (apiKey) headers['X-API-Key'] = apiKey;
        const response = await fetch('/api/v1/analyze/detailed', {
            method: 'POST',
            headers,
            body: JSON.stringify(request)
        });

        hideThinking();

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }

        const data = await response.json();

        // DEBUG: Log entire API response
        console.log('=== API RESPONSE ===');
        console.log('Full response:', data);
        console.log('extractedIntelligence:', data.extractedIntelligence);
        console.log('====================');

        // Add scammer message to history
        conversationHistory.push({
            sender: 'scammer',
            text: text,
            timestamp: timestamp
        });

        // Add agent response if available
        if (data.agentResponse) {
            addMessage('agent', data.agentResponse, true);
            conversationHistory.push({
                sender: 'user',
                text: data.agentResponse,
                timestamp: new Date().toISOString()
            });
        }

        // Update UI
        console.log('Calling updateMetrics...');
        updateMetrics(data);
        console.log('Calling updateIntelligence...');
        updateIntelligence(data.extractedIntelligence);
        console.log('UI update complete');

    } catch (error) {
        hideThinking();
        console.error('Error:', error);
        alert(`Error: ${error.message}`);
    } finally {
        isProcessing = false;
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send';
    }
}

function resetConversation() {
    conversationHistory = [];
    startTime = null;

    // Reset UI
    chatMessages.innerHTML = `
        <div class="empty-state">
            <p>Start a conversation by typing a scam message below.</p>
            <p style="margin-top: 10px; font-size: 0.8rem;">Example: "Your bank account has been compromised. Send OTP to verify."</p>
        </div>
    `;

    statusBadge.textContent = 'Monitoring';
    statusBadge.className = 'status-badge monitoring';

    document.getElementById('scamDetected').textContent = '-';
    document.getElementById('scamDetected').className = 'metric-value';
    document.getElementById('confidence').textContent = '-';
    document.getElementById('confidence').className = 'metric-value';
    document.getElementById('confidenceBar').style.width = '0%';
    document.getElementById('messagesCount').textContent = '0';
    document.getElementById('duration').textContent = '0s';
    document.getElementById('agentNotes').textContent = '-';
    document.getElementById('intelligenceContent').innerHTML = 
        '<div class="empty-state"><p>No intelligence extracted yet.</p></div>';
}

// Focus input on load
messageInput.focus();
