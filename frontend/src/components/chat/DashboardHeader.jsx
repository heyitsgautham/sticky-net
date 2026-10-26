// Fixed top bar of the chat dashboard with the API connection light.
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Bug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export const DashboardHeader = ({ connectionStatus }) => {
  const navigate = useNavigate();
  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-panel border-b border-white/10">
      <div className="max-w-[1800px] mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/")}
            className="text-gray-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <div className="h-6 w-px bg-white/10" />
          <div className="flex items-center gap-2">
            <Bug className="w-6 h-6 text-cyber-cyan" />
            <span className="font-heading font-bold text-xl text-white">Sticky-Net</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                connectionStatus === "connected"
                  ? "bg-green-400"
                  : connectionStatus === "disconnected"
                    ? "bg-red-400"
                    : "bg-yellow-400"
              }`}
            />
            <span className="text-xs text-gray-400 font-mono">
              {connectionStatus === "connected"
                ? "API Connected"
                : connectionStatus === "disconnected"
                  ? "API Offline"
                  : "Checking..."}
            </span>
          </div>
          <Badge className="border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10 font-mono">
            CONVERSATION TESTER
          </Badge>
        </div>
      </div>
    </header>
  );
};
