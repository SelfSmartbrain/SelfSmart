"use client";

import ReactMarkdown from 'react-markdown';
import { cn } from "@/lib/utils";
import { Message } from "@/store/useChatStore";
import { User, Bot, ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from 'react';

interface ChatMessageProps {
  message: Message;
  index: number;
  conversationId: string | null;
}

export function ChatMessage({ message, index, conversationId }: ChatMessageProps) {
  const isAssistant = message.role === 'assistant';
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);

  const handleFeedback = async (isPositive: boolean) => {
    if (!conversationId) return;

    try {
      await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message_index: index,
          is_positive: isPositive,
        }),
      });
      setFeedback(isPositive ? 'positive' : 'negative');
    } catch (error) {
      console.error('Failed to send feedback:', error);
    }
  };

  return (
    <div className={cn(
      "flex w-full gap-4 p-6 transition-colors group",
      isAssistant ? "bg-accent/50" : "bg-background"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
        isAssistant ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
      )}>
        {isAssistant ? <Bot size={20} /> : <User size={20} />}
      </div>

      <div className="flex-1 min-w-0 space-y-2 overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="font-semibold text-sm">
            {isAssistant ? "SmartSelf AI" : "You"}
          </div>

          {isAssistant && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon"
                className={cn("h-7 w-7", feedback === 'positive' && "text-green-500")}
                onClick={() => handleFeedback(true)}
              >
                <ThumbsUp size={14} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn("h-7 w-7", feedback === 'negative' && "text-red-500")}
                onClick={() => handleFeedback(false)}
              >
                <ThumbsDown size={14} />
              </Button>
            </div>
          )}
        </div>

        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
          <ReactMarkdown>
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
