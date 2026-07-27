import { useChatStore } from "@/store/useChatStore";
import { apiUrl } from "@/lib/api";

export const useStreamingChat = () => {
  const { updateLastAssistantMessage, addMessage, setLoading, conversationId, setConversationId, fetchConversations } = useChatStore();

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

    let isNewConversation = !conversationId;

    try {
       const response = await fetch(apiUrl('/api/chat/stream'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
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

              if (data.conversation_id && isNewConversation) {
                setConversationId(data.conversation_id);
                isNewConversation = false; // Prevents multiple calls
                fetchConversations();
              }
            } catch {
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
      // Fetch conversations to update title (LLM updates it asynchronously)
      fetchConversations();
    }
  };

  return { sendMessage };
};
