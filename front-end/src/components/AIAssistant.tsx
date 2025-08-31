// src/components/AIAssistant.tsx
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, User, Bot, Loader2 } from "lucide-react";
import { api, Note, ChatMessage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface AIAssistantProps {
  currentNote: Note | undefined;
  allNotes: Note[]; // Kept for future @-mention functionality
  collapsed: boolean;
}

export function AIAssistant({ currentNote, allNotes, collapsed }: AIAssistantProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: "Hello! I can answer questions based on the content of your currently open note."
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset chat when the note changes
  useEffect(() => {
    setMessages([{
      role: 'assistant',
      content: "Hello! I can answer questions based on the content of your currently open note."
    }]);
  }, [currentNote?.id]);

  const handleSend = async () => {
    if (!input.trim() || !currentNote) {
        if (!currentNote) {
            toast({
                title: "No Note Selected",
                description: "Please select a note to ask questions about it.",
                variant: "destructive"
            });
        }
        return;
    }

    const userMessage: ChatMessage = { role: 'user', content: input };
    const currentHistory = messages.filter(m => m.role !== 'assistant' || m.content !== "Hello! I can answer questions based on the content of your currently open note.");

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await api.askAssistant({
        question: input,
        note_context: currentNote.text,
        history: currentHistory,
      });
      const assistantMessage: ChatMessage = { role: 'assistant', content: response.answer };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      toast({ title: "Assistant Error", description: String(error), variant: "destructive" });
       setMessages(prev => prev.slice(0, -1)); // Remove the user's message on error
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (collapsed) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-panel-border">
        <h2 className="font-semibold text-foreground flex items-center gap-2">
          <Bot className="h-5 w-5 text-ai-primary" />
          AI Assistant
        </h2>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-muted-foreground" />
                </div>
              )}
              <div className={`max-w-[80%] p-3 rounded-lg text-sm leading-relaxed ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}>
                {message.content}
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                  <User className="h-4 w-4 text-secondary-foreground" />
                </div>
              )}
            </div>
          ))}
           {isLoading && (
             <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                    <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
                </div>
                <div className="max-w-[80%] p-3 rounded-lg text-sm leading-relaxed bg-muted text-foreground">
                    Thinking...
                </div>
             </div>
           )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-panel-border">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={currentNote ? "Ask about the current note..." : "Select a note first..."}
            disabled={isLoading || !currentNote}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()} className="px-3">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}