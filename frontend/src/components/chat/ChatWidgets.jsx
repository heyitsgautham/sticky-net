// Presentational pieces of the chat dashboard.
import React from "react";
import { Copy, AlertTriangle, Zap, Trash2, History, CreditCard, Phone, Mail, Link2, Building2 } from "lucide-react";

// ============ SPIDER WEB BACKGROUND ============
export const WebPattern = () => (
    <div className="fixed inset-0 overflow-hidden pointer-events-none opacity-20">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
            {Array.from({ length: 12 }).map((_, i) => {
                const angle = (i / 12) * 2 * Math.PI;
                return (
                    <line
                        key={`spoke-${i}`}
                        x1="50"
                        y1="50"
                        x2={50 + Math.cos(angle) * 50}
                        y2={50 + Math.sin(angle) * 50}
                        stroke="#00F5D4"
                        strokeWidth="0.15"
                        opacity="0.3"
                    />
                );
            })}
            {[1, 2, 3, 4, 5].map((ring) => (
                <circle
                    key={`ring-${ring}`}
                    cx="50"
                    cy="50"
                    r={ring * 10}
                    fill="none"
                    stroke="#00F5D4"
                    strokeWidth="0.1"
                    opacity="0.2"
                />
            ))}
        </svg>
    </div>
);

// ============ GLASS CONTAINER ============
export const GlassPanel = ({ children, className = "", glowOnHover = true }) => (
    <div
        className={`
      glass-panel rounded-2xl border border-white/10 
      ${glowOnHover ? 'hover:border-cyber-cyan/30 hover:shadow-cyan-glow' : ''}
      transition-all duration-300
      ${className}
    `}
    >
        {children}
    </div>
);

// ============ CHAT MESSAGE ============
export const ChatMessage = React.memo(({ message, isAgent }) => (
    <div className={`flex ${isAgent ? 'justify-end' : 'justify-start'} mb-4`}>
        <div
            className={`
        max-w-[80%] px-4 py-3 rounded-2xl font-mono text-sm
        ${isAgent
                    ? 'bg-cyber-cyan/20 border border-cyber-cyan/30 text-cyber-cyan ml-auto rounded-br-sm'
                    : 'bg-white/5 border border-white/10 text-gray-200 rounded-bl-sm'
                }
      `}
        >
            <p className="leading-relaxed whitespace-pre-wrap">{message.text}</p>
        </div>
    </div>
));

// ============ METRIC CARD ============
export const MetricCard = React.memo(({ label, value, icon: Icon, color = "cyan" }) => {
    const colorClasses = {
        cyan: "text-cyber-cyan border-cyber-cyan/30",
        red: "text-cyber-red border-cyber-red/30",
        green: "text-green-400 border-green-400/30",
        yellow: "text-yellow-400 border-yellow-400/30",
    };

    return (
        <div className={`flex items-center justify-between py-3 border-b border-white/5 last:border-0`}>
            <div className="flex items-center gap-2">
                {Icon && <Icon className={`w-4 h-4 ${colorClasses[color]?.split(' ')[0]}`} />}
                <span className="text-gray-400 text-sm">{label}</span>
            </div>
            <span className={`font-mono font-bold ${colorClasses[color]?.split(' ')[0]}`}>
                {value}
            </span>
        </div>
    );
});

// ============ INTEL TAG ============
export const IntelTag = React.memo(({ type, value }) => {
    const typeConfig = {
        upi: { 
            icon: CreditCard, 
            label: "UPI ID",
            color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" 
        },
        link: { 
            icon: Link2, 
            label: "Link",
            color: "bg-red-500/20 text-red-400 border-red-500/30" 
        },
        phone: { 
            icon: Phone, 
            label: "Phone",
            color: "bg-purple-500/20 text-purple-400 border-purple-500/30" 
        },
        bank: { 
            icon: Building2, 
            label: "Bank A/C",
            color: "bg-blue-500/20 text-blue-400 border-blue-500/30" 
        },
        email: { 
            icon: Mail, 
            label: "Email",
            color: "bg-green-500/20 text-green-400 border-green-500/30" 
        },
        name: { 
            icon: Building2, 
            label: "Name",
            color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" 
        },
        ifsc: { 
            icon: Building2, 
            label: "IFSC",
            color: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30" 
        },
        whatsapp: { 
            icon: Phone, 
            label: "WhatsApp",
            color: "bg-pink-500/20 text-pink-400 border-pink-500/30" 
        },
        bankName: { 
            icon: Building2, 
            label: "Bank Name",
            color: "bg-teal-500/20 text-teal-400 border-teal-500/30" 
        },
        other: { 
            icon: AlertTriangle, 
            label: "Other",
            color: "bg-amber-500/20 text-amber-400 border-amber-500/30" 
        },
    };

    const config = typeConfig[type] || typeConfig.upi;
    const IconComponent = config.icon;

    const handleCopy = () => {
        navigator.clipboard.writeText(value);
    };

    return (
        <div
            className={`
        flex items-center gap-2 px-3 py-2 rounded-lg border font-mono text-xs
        ${config.color}
      `}
        >
            <IconComponent className="w-4 h-4 flex-shrink-0" />
            <span className="font-semibold flex-shrink-0">{config.label}:</span>
            <span className="truncate flex-1">{value}</span>
            <button onClick={handleCopy} className="ml-auto hover:opacity-70 transition-opacity flex-shrink-0">
                <Copy className="w-3 h-3" />
            </button>
        </div>
    );
});

// ============ CONVERSATION CARD ============
export const ConversationCard = React.memo(({ conversation, onClick, isActive, onDelete }) => (
    <div
        className={`
      w-full text-left p-4 rounded-xl border transition-all duration-300 relative group
      ${isActive
                ? 'bg-cyber-cyan/10 border-cyber-cyan/50 shadow-cyan-glow'
                : 'bg-white/5 border-white/10 hover:border-white/20'
            }
    `}
    >
        <button onClick={onClick} className="w-full text-left">
            <div className="flex items-center gap-2 mb-2">
                {conversation.isSample ? (
                    <Zap className="w-4 h-4 text-yellow-400" />
                ) : (
                    <History className="w-4 h-4 text-cyber-cyan" />
                )}
                <span className="font-semibold text-white text-sm truncate flex-1">
                    {conversation.title}
                </span>
            </div>
            <p className="text-gray-500 text-xs font-mono truncate">{conversation.preview}</p>
            <div className="flex items-center gap-3 mt-2">
                {conversation.metrics?.confidence && (
                    <span className="text-[10px] text-cyber-cyan font-mono">
                        {(conversation.metrics.confidence * 100).toFixed(0)}% conf
                    </span>
                )}
                <span className="text-[10px] text-gray-500">
                    {conversation.messages?.length || 0} msgs
                </span>
            </div>
        </button>
        {!conversation.isSample && onDelete && (
            <button
                onClick={(e) => { e.stopPropagation(); onDelete(conversation.id); }}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-500/20 rounded"
            >
                <Trash2 className="w-3 h-3 text-red-400" />
            </button>
        )}
    </div>
));

ChatMessage.displayName = "ChatMessage";
MetricCard.displayName = "MetricCard";
IntelTag.displayName = "IntelTag";
ConversationCard.displayName = "ConversationCard";
