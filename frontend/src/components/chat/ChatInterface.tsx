"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/store/useChatStore";
import { useStreamingChat } from "@/hooks/useStreamingChat";
import { ChatMessage } from "./ChatMessage";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2 } from "lucide-react";

export function ChatInterface() {
  const [input, setInput] = useState("");
  const { messages, isLoading, conversationId } = useChatStore();
  const { sendMessage } = useStreamingChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput("");
    await sendMessage(message);
  };

  useEffect(() => {
    if (scrollRef.current) {
      const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <ScrollArea ref={scrollRef} className="flex-1">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[60vh] text-center px-4">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-6 text-primary">
              <Send size={32} />
            </div>
            <h2 className="text-2xl font-bold mb-2">Welcome to SmartSelf AI</h2>
            <p className="text-muted-foreground max-w-md">
              Your autonomous learning assistant. Ask me anything about retail intelligence,
              demand forecasting, or latest market trends.
            </p>
          </div>
        ) : (
          <div className="flex flex-col divide-y">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                message={msg}
                index={i}
                conversationId={conversationId}
              />
            ))}
          </div>
        )}
      </ScrollArea>

      <div className="p-4 border-t bg-background">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !input.trim()}>
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
        <p className="text-[10px] text-center mt-2 text-muted-foreground">
          SmartSelf AI may produce inaccurate information about people, places, or facts.
        </p>
      </div>
    </div>
  );
}
