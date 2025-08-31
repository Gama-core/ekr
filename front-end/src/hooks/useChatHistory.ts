// src/hooks/useChatHistory.ts
import { useState, useEffect, useCallback } from 'react';
import { Message } from '@/pages/Chatbot'; // This will be exported from Chatbot.tsx

const STORAGE_KEY = 'chat-history-sessions';

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  timestamp: number;
}

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Load sessions from localStorage on initial render
  useEffect(() => {
    try {
      const savedSessions = localStorage.getItem(STORAGE_KEY);
      const parsedSessions: ChatSession[] = savedSessions ? JSON.parse(savedSessions) : [];
      setSessions(parsedSessions);

      if (parsedSessions.length > 0) {
        // Sort by most recent and activate the latest one
        const sortedSessions = parsedSessions.sort((a, b) => b.timestamp - a.timestamp);
        setActiveSessionId(sortedSessions[0].id);
      } else {
        // If no sessions, create a new one
        startNewSession();
      }
    } catch (error) {
      console.error("Failed to load chat sessions from localStorage", error);
      startNewSession();
    }
  }, []); // The empty dependency array ensures this runs only once on mount

  const saveSessionsToStorage = (updatedSessions: ChatSession[]) => {
    const sortedSessions = updatedSessions.sort((a, b) => b.timestamp - a.timestamp);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sortedSessions));
    setSessions(sortedSessions);
  };

  const startNewSession = useCallback(() => {
    const newSession: ChatSession = {
      id: `session_${Date.now()}`,
      title: 'New Conversation',
      messages: [],
      timestamp: Date.now(),
    };
    // Use a function for setSessions to get the latest state
    setSessions(prevSessions => {
        const updatedSessions = [newSession, ...prevSessions];
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updatedSessions));
        return updatedSessions;
    });
    setActiveSessionId(newSession.id);
    return newSession.id;
  }, []);

  const deleteSession = (sessionId: string) => {
    const updatedSessions = sessions.filter(s => s.id !== sessionId);
    saveSessionsToStorage(updatedSessions);

    if (activeSessionId === sessionId) {
      if (updatedSessions.length > 0) {
        setActiveSessionId(updatedSessions[0].id);
      } else {
        // If the last session was deleted, create a new one
        startNewSession();
      }
    }
  };

  const updateSessionMessages = (sessionId: string, messages: Message[]) => {
    const updatedSessions = sessions.map(s =>
      s.id === sessionId
      ? {
          ...s,
          messages,
          timestamp: Date.now(),
          // Auto-title the session based on the first user message
          title: s.title === 'New Conversation' && messages[0]?.type === 'user'
            ? messages[0].content.substring(0, 40) + (messages[0].content.length > 40 ? '...' : '')
            : s.title,
        }
      : s
    );
    saveSessionsToStorage(updatedSessions);
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);

  return {
    sessions,
    activeSession,
    activeSessionId,
    setActiveSessionId,
    startNewSession,
    deleteSession,
    updateSessionMessages
  };
}