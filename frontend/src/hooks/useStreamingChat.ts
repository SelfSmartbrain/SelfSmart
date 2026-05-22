import { useChatStore } from "@/store/useChatStore";

export const useStreamingChat = () => {
  const { updateLastAssistantMessage, addMessage, setLoading, conversationId, setConversationId } = useChatStore();

  const sendMessage = async (content: string) => {
    if (!content.trim()) return;

    setLoading(true);
    
    // Add user message immediately
    const userMessage = {
      role: 'user' as const,
      content,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);

    try {
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.text) {
                updateLastAssistantMessage(data.text);
              }
              
              if (data.conversation_id && !conversationId) {
                setConversationId(data.conversation_id);
              }
            } catch (e) {
              // Sometimes chunks are incomplete, ignore parse errors for partial JSON
              continue;
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming chat error:', error);
      updateLastAssistantMessage("\n\n*Error: Failed to connect to the assistant. Please ensure the backend is running.*");
    } finally {
      setLoading(false);
    }
  };

  return { sendMessage };
};
