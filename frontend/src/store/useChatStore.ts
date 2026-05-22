import { create } from 'zustand';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  conversationId: string | null;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setLoading: (loading: boolean) => void;
  setConversationId: (id: string) => void;
  updateLastAssistantMessage: (content: string) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  conversationId: null,
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  setMessages: (messages) => set({ messages }),
  setLoading: (loading) => set({ isLoading: loading }),
  setConversationId: (id) => set({ conversationId: id }),
  updateLastAssistantMessage: (content) => set((state) => {
    const newMessages = [...state.messages];
    const lastMessage = newMessages[newMessages.length - 1];
    if (lastMessage && lastMessage.role === 'assistant') {
      newMessages[newMessages.length - 1] = {
        ...lastMessage,
        content: lastMessage.content + content,
      };
    } else {
      newMessages.push({
        role: 'assistant',
        content: content,
        timestamp: new Date().toISOString(),
      });
    }
    return { messages: newMessages };
  }),
  clearChat: () => set({ messages: [], conversationId: null }),
}));
