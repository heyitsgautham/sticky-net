// Left-hand column of the chat dashboard: example and saved conversations.
import { History, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConversationCard, GlassPanel } from "@/components/chat/ChatWidgets";
import { sampleConversations } from "@/data/sampleConversations";

export const ConversationSidebar = ({
    savedConversations,
    currentConversationId,
    onNew,
    onSelect,
    onDelete,
}) => (
        <div className="col-span-12 lg:col-span-2 h-full min-h-0">
            <GlassPanel className="h-full p-4 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-4 flex-shrink-0">
                    <h3 className="text-white font-semibold flex items-center gap-2">
                        <History className="w-4 h-4 text-cyber-cyan" />
                        Conversations
                    </h3>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={onNew}
                        className="h-8 w-8 p-0 text-cyber-cyan hover:bg-cyber-cyan/10"
                    >
                        <Plus className="w-4 h-4" />
                    </Button>
                </div>

                <div className="flex-1 min-h-0 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
                    <div className="space-y-3">
                        {/* Sample Conversations */}
                        <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Examples</div>
                    {sampleConversations.map((conv) => (
                        <ConversationCard
                            key={conv.id}
                            conversation={conv}
                            isActive={currentConversationId === conv.id}
                            onClick={() => onSelect(conv)}
                        />
                    ))}

                    {/* Saved Conversations */}
                    {savedConversations.length > 0 && (
                        <>
                            <div className="text-xs text-gray-500 uppercase tracking-wider mt-4 mb-2">Your Chats</div>
                            {savedConversations.map((conv) => (
                                <ConversationCard
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={currentConversationId === conv.id}
                                    onClick={() => onSelect(conv)}
                                    onDelete={onDelete}
                                />
                            ))}
                        </>
                    )}
                    </div>
                </div>
            </GlassPanel>
        </div>
);
