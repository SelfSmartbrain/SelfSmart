import { create } from 'zustand';
import { apiUrl } from '@/lib/api';

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ConversationHeader {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  conversationId: string | null;
  conversations: ConversationHeader[];
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  setLoading: (loading: boolean) => void;
  setConversationId: (id: string | null) => void;
  updateLastAssistantMessage: (content: string) => void;
  clearChat: () => void;
  setConversations: (conversations: ConversationHeader[]) => void;
  fetchConversations: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  conversationId: null,
  conversations: [],
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
  setConversations: (conversations) => set({ conversations }),
   fetchConversations: async () => {
     const token = localStorage.getItem('token');
     if (!token) return;
     try {
       const response = await fetch(apiUrl('/api/conversations'), {
         headers: {
           'Authorization': `Bearer ${token}`
         }
       });
       if (response.ok) {
         const data = await response.json();
         set({ conversations: data });
       }
     } catch (e) {
       console.error('Failed to fetch conversations:', e);
     }
   },
   selectConversation: async (id) => {
     const token = localStorage.getItem('token');
     if (!token) return;
     set({ isLoading: true, conversationId: id });
     try {
       const response = await fetch(apiUrl(`/api/conversations/${id}`), {
         headers: {
           'Authorization': `Bearer ${token}`
         }
       });
       if (response.ok) {
         const data = await response.json();
         // Convert dates if needed, backend sends ISO strings
         const formattedMessages = data.messages.map((m: any) => ({
           role: m.role,
           content: m.content,
           timestamp: m.timestamp
         }));
         set({ messages: formattedMessages });
       }
     } catch (e) {
       console.error('Failed to select conversation:', e);
     } finally {
       set({ isLoading: false });
     }
   },
   deleteConversation: async (id) => {
     const token = localStorage.getItem('token');
     if (!token) return;
     try {
       const response = await fetch(apiUrl(`/api/conversations/${id}`), {
         method: 'DELETE',
         headers: {
           'Authorization': `Bearer ${token}`
         }
       });
       if (response.ok) {
         set((state) => {
           const newConversations = state.conversations.filter(c => c.id !== id);
           const activeId = state.conversationId === id ? null : state.conversationId;
           const activeMessages = state.conversationId === id ? [] : state.messages;
           return {
             conversations: newConversations,
             conversationId: activeId,
             messages: activeMessages
           };
         });
       }
     } catch (e) {
       console.error('Failed to delete conversation:', e);
     }
   }
}));
