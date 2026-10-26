// Right-hand column of the chat dashboard: request settings, detection metrics,
// the extraction feed and the agent's notes.
import { AlertTriangle, CheckCircle, MessageSquare, Shield, Zap } from "lucide-react";
import { GlassPanel, IntelTag, MetricCard } from "@/components/chat/ChatWidgets";

export const AnalysisSidebar = ({
  channel,
  setChannel,
  locale,
  setLocale,
  metrics,
  extractionOrder,
  agentNotes,
}) => (
  <div className="col-span-12 lg:col-span-4 h-full min-h-0 flex flex-col gap-4 md:gap-6">
    {/* Configuration */}
    <GlassPanel className="p-5 flex-shrink-0">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <Shield className="w-4 h-4 text-gray-400" />
        Configuration
      </h3>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label htmlFor="channel-select" className="text-gray-500 text-xs mb-1 block">
            CHANNEL
          </label>
          <select
            id="channel-select"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-cyber-cyan"
          >
            <option value="SMS">SMS</option>
            <option value="WhatsApp">WhatsApp</option>
            <option value="Email">Email</option>
          </select>
        </div>
        <div>
          <label htmlFor="locale-select" className="text-gray-500 text-xs mb-1 block">
            LOCALE
          </label>
          <select
            id="locale-select"
            value={locale}
            onChange={(e) => setLocale(e.target.value)}
            className="w-full bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-cyber-cyan"
          >
            <option value="IN">India (IN)</option>
            <option value="US">USA (US)</option>
            <option value="UK">UK (UK)</option>
          </select>
        </div>
      </div>
    </GlassPanel>

    {/* Detection Metrics */}
    <GlassPanel className="p-5 flex-shrink-0">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-cyber-red" />
        Detection Metrics
      </h3>
      <div className="space-y-1">
        <MetricCard
          label="Scam Detected"
          value={metrics.scamDetected === null ? "-" : metrics.scamDetected ? "YES" : "NO"}
          icon={metrics.scamDetected ? AlertTriangle : CheckCircle}
          color={metrics.scamDetected ? "red" : "green"}
        />
        <MetricCard
          label="Confidence"
          value={metrics.confidence !== null ? `${(metrics.confidence * 100).toFixed(0)}%` : "-"}
          color={metrics.confidence > 0.8 ? "red" : metrics.confidence > 0.5 ? "yellow" : "green"}
        />
        <div className="h-2 bg-white/5 rounded-full overflow-hidden mt-2 mb-3">
          <div
            className={`h-full transition-all duration-500 ease-out ${metrics.confidence > 0.8 ? "bg-cyber-red" : metrics.confidence > 0.5 ? "bg-yellow-400" : "bg-green-400"}`}
            style={{ width: `${(metrics.confidence || 0) * 100}%` }}
          />
        </div>
        <MetricCard
          label="Messages Exchanged"
          value={metrics.messagesExchanged}
          icon={MessageSquare}
          color="cyan"
        />
      </div>
    </GlassPanel>

    {/* Extracted Intelligence */}
    <GlassPanel className="p-5 flex-1 min-h-0 overflow-hidden flex flex-col">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2 flex-shrink-0">
        <Zap className="w-4 h-4 text-yellow-400" />
        Extracted Intelligence
      </h3>
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin space-y-2 pr-2">
        {extractionOrder.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-600 text-sm font-mono">
            No intelligence extracted yet.
          </div>
        ) : (
          <>
            {extractionOrder.map((item, idx) => (
              <IntelTag key={`extracted-${idx}`} type={item.type} value={item.value} />
            ))}
          </>
        )}
      </div>
    </GlassPanel>

    {/* Agent Notes */}
    <GlassPanel className="p-5 flex-shrink-0">
      <h3 className="text-white font-semibold mb-3 flex items-center gap-2">📝 Agent Notes</h3>
      <p className="text-gray-400 text-sm font-mono leading-relaxed whitespace-pre-wrap">
        {agentNotes || "-"}
      </p>
    </GlassPanel>
  </div>
);
