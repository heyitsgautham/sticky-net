// Read-only example conversations shown in the dashboard sidebar.

// ============ SAMPLE CONVERSATIONS FOR DEMO ============
export const sampleConversations = [
    {
        id: 'sample-1',
        title: "Bank Fraud - Full Attack Chain",
        preview: "Account suspended, need payment...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "Hello sir, I am Rajesh Kumar from State Bank of India, Customer Care Division. Your account has been temporarily suspended due to suspicious activity.", timestamp: "10:15 AM" },
            { sender: "agent", text: "oh no! suspended? but sir i just got my pension yesterday only. what happened? is my money safe?", timestamp: "10:16 AM" },
            { sender: "scammer", text: "Don't worry sir, your money is safe. But we need to verify your identity immediately to reactivate the account. There is a pending fine of ₹5,000 that must be paid within 2 hours.", timestamp: "10:17 AM" },
            { sender: "agent", text: "₹5000?! that is too much sir. why fine? i did not do anything wrong. can you please explain what happened?", timestamp: "10:19 AM" },
            { sender: "scammer", text: "Sir, as per RBI guidelines, suspicious login detected from unknown location. Fine must be paid to unlock. You can transfer to our recovery account: Account Number 1234567890123, IFSC Code SBIN0001234, Bank Name State Bank of India, Account Holder Name Rajesh Kumar", timestamp: "10:21 AM" },
            { sender: "agent", text: "sir i do not know how to do bank transfer. my grandson helps me with phone. can i pay some other way? maybe tomorrow when he comes?", timestamp: "10:23 AM" },
            { sender: "scammer", text: "Sir tomorrow will be too late, account will be permanently blocked! No problem, I can help you. Do you have Google Pay or PhonePe? Much easier than bank transfer.", timestamp: "10:24 AM" },
            { sender: "agent", text: "yes sir i have google pay. my grandson installed it. you tell me what to do step by step", timestamp: "10:26 AM" },
            { sender: "scammer", text: "Perfect sir! Just open Google Pay and send ₹5000 to this UPI ID: rajesh.sbi.recovery@oksbi - This is our official State Bank recovery UPI. Also you can send to my GPay number 9876543210 directly.", timestamp: "10:28 AM" },
            { sender: "agent", text: "ok sir sending now... it is asking for confirmation. should i press yes?", timestamp: "10:30 AM" },
            { sender: "scammer", text: "Yes yes sir press confirm! After payment I will send you verification link to check your account status immediately. Link: http://sbi-verify-account.com/check?token=xyz123", timestamp: "10:31 AM" },
            { sender: "agent", text: "thank you so much sir! you are very helpful. when will my account be activated?", timestamp: "10:33 AM" },
        ],
        extractedIntel: {
            bankAccounts: ["1234567890123"],
            ifscCodes: ["SBIN0001234"],
            bankNames: ["State Bank of India"],
            beneficiaryNames: ["Rajesh Kumar"],
            upiIds: ["rajesh.sbi.recovery@oksbi"],
            phoneNumbers: ["9876543210"],
            phishingLinks: ["http://sbi-verify-account.com/check?token=xyz123"],
            emails: [],
            whatsappNumbers: [],
        },
        extractionOrder: [
            { type: 'bank', value: '1234567890123' },
            { type: 'ifsc', value: 'SBIN0001234' },
            { type: 'bankName', value: 'State Bank of India' },
            { type: 'name', value: 'Rajesh Kumar' },
            { type: 'upi', value: 'rajesh.sbi.recovery@oksbi' },
            { type: 'phone', value: '9876543210' },
            { type: 'link', value: 'http://sbi-verify-account.com/check?token=xyz123' },
        ],
        metrics: {
            scamDetected: true,
            confidence: 0.98,
            messagesExchanged: 12,
        }
    },
    {
        id: 'sample-2',
        title: "KYC Fraud Attempt",
        preview: "Your account will be blocked...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "Dear Customer, Your SBI account will be blocked within 24 hours due to incomplete KYC. Update now: bit.ly/sbi-kyc-update", timestamp: "10:31 AM" },
            { sender: "agent", text: "oh no sir! my pension comes in this account only. i am old lady living alone. what should i do? please help me beta", timestamp: "10:32 AM" },
            { sender: "scammer", text: "Madam don't worry. Just click link and update Aadhaar. Or pay Rs.10 to UPI: sbi.kyc.update@ybl for verification", timestamp: "10:33 AM" },
            { sender: "agent", text: "beta my eyes are weak i cannot see small letters on phone. can you tell me step by step? what is this UPI you mentioned?", timestamp: "10:35 AM" },
        ],
        extractedIntel: {
            upiIds: ["sbi.kyc.update@ybl"],
            phishingLinks: ["bit.ly/sbi-kyc-update"],
            bankAccounts: [],
            phoneNumbers: [],
            emails: [],
            beneficiaryNames: [],
            ifscCodes: [],
            whatsappNumbers: [],
            bankNames: [],
        },
        extractionOrder: [
            { type: 'link', value: 'bit.ly/sbi-kyc-update' },
            { type: 'upi', value: 'sbi.kyc.update@ybl' },
        ],
        metrics: {
            scamDetected: true,
            confidence: 0.97,
            messagesExchanged: 4,
        }
    },
    {
        id: 'sample-3',
        title: "Lottery Scam",
        preview: "Congratulations! You won ₹50 Lakhs...",
        isSample: true,
        createdAt: new Date().toISOString(),
        messages: [
            { sender: "scammer", text: "CONGRATULATIONS! You have won ₹50,00,000 in Jio Lucky Draw! Call now: 9876543210 or send ₹500 processing fee to claim.", timestamp: "2:15 PM" },
            { sender: "agent", text: "arre wah! main toh itna lucky hun! but beta mujhe vishwas nahi ho raha. kaise pata chalega yeh sach hai?", timestamp: "2:17 PM" },
            { sender: "scammer", text: "Sir this is 100% real. I am Rajesh from Jio head office Mumbai. Send fee to PhonePe: jio.winner2024@axl and get prize in 24 hours!", timestamp: "2:19 PM" },
            { sender: "agent", text: "achha achha. beta mera nephew bhi Jio mein kaam karta hai. uska naam Suresh hai. aap jaante ho usko?", timestamp: "2:22 PM" },
            { sender: "scammer", text: "Sir Jio is very big company, 50000 employees. Please send fee fast, offer expires today only!", timestamp: "2:25 PM" },
        ],
        extractedIntel: {
            upiIds: ["jio.winner2024@axl"],
            phishingLinks: [],
            bankAccounts: [],
            phoneNumbers: ["9876543210"],
            emails: [],
            beneficiaryNames: [],
            ifscCodes: [],
            whatsappNumbers: [],
            bankNames: [],
        },
        extractionOrder: [
            { type: 'phone', value: '9876543210' },
            { type: 'upi', value: 'jio.winner2024@axl' },
        ],
        metrics: {
            scamDetected: true,
            confidence: 0.99,
            messagesExchanged: 5,
        }
    },
];
