import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Send, User, Bot, FileText, Check } from "lucide-react";

interface Note {
  id: number;
  parent_id: number | null;
  title: string;
  text: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIAssistantProps {
  currentNote: Note | undefined;
  allNotes: Note[];
  collapsed: boolean;
}

export function AIAssistant({ currentNote, allNotes, collapsed }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "Hello! I'm your AI assistant. I can help you analyze your notes, answer questions, and provide insights. Try typing '@' to reference specific notes in your questions."
    }
  ]);
  const [input, setInput] = useState('');
  const [showNoteSuggestions, setShowNoteSuggestions] = useState(false);
  const [selectedNotes, setSelectedNotes] = useState<Note[]>([]);
  const [filteredNotes, setFilteredNotes] = useState<Note[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleInputChange = (value: string) => {
    setInput(value);
    
    // Check if user typed '@'
    if (value.includes('@')) {
      const lastAtIndex = value.lastIndexOf('@');
      const searchTerm = value.substring(lastAtIndex + 1).toLowerCase();
      
      if (searchTerm.length >= 0) {
        const filtered = allNotes.filter(note => 
          note.title.toLowerCase().includes(searchTerm)
        );
        setFilteredNotes(filtered);
        setShowNoteSuggestions(true);
      }
    } else {
      setShowNoteSuggestions(false);
    }
  };

  const selectNote = (note: Note) => {
    const lastAtIndex = input.lastIndexOf('@');
    const beforeAt = input.substring(0, lastAtIndex);
    const afterAt = input.substring(input.indexOf(' ', lastAtIndex) !== -1 ? input.indexOf(' ', lastAtIndex) : input.length);
    
    setInput(beforeAt + '@' + note.title + ' ' + afterAt);
    setSelectedNotes(prev => [...prev, note]);
    setShowNoteSuggestions(false);
    inputRef.current?.focus();
  };

  const removeSelectedNote = (noteId: number) => {
    setSelectedNotes(prev => prev.filter(note => note.id !== noteId));
  };

  const handleSend = () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);

    // Simulate AI response
    setTimeout(() => {
      const responses = [
        "Based on your note, I can see several key insights. The main themes revolve around product strategy and user experience improvements.",
        "That's an interesting question! Looking at the content you've shared, I notice patterns in your user research findings that suggest focusing on AI-assisted features.",
        "From analyzing your notes, it appears that market expansion should be approached methodically, starting with the most promising segments identified in your competitive analysis.",
        "Your meeting notes indicate strong team collaboration. The action items suggest a well-structured approach to feature development and stakeholder communication."
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      const assistantMessage: Message = { role: 'assistant', content: randomResponse };
      setMessages(prev => [...prev, assistantMessage]);
    }, 1000);

    setInput('');
    setSelectedNotes([]);
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
      {/* Header */}
      <div className="p-4 border-b border-panel-border">
        <h2 className="font-semibold text-foreground flex items-center gap-2">
          <Bot className="h-5 w-5 text-ai-primary" />
          AI Assistant
        </h2>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-ai-primary flex items-center justify-center flex-shrink-0">
                  <Bot className="h-4 w-4 text-white" />
                </div>
              )}
              
              <div
                className={`max-w-[80%] p-3 rounded-lg text-sm leading-relaxed ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-foreground'
                }`}
              >
                {message.content}
              </div>
              
              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                  <User className="h-4 w-4 text-secondary-foreground" />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-4 border-t border-panel-border space-y-3 relative">
        {/* Selected Notes */}
        {selectedNotes.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selectedNotes.map((note) => (
              <div
                key={note.id}
                className="flex items-center gap-1 px-2 py-1 bg-ai-secondary text-ai-primary rounded text-xs border border-ai-border"
              >
                <FileText className="h-3 w-3" />
                <span>{note.title}</span>
                <button
                  onClick={() => removeSelectedNote(note.id)}
                  className="hover:text-destructive"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Note Suggestions */}
        {showNoteSuggestions && filteredNotes.length > 0 && (
          <Card className="absolute bottom-24 left-0 right-0 max-h-48 overflow-y-auto z-10 p-2">
            <div className="space-y-1">
              {filteredNotes.slice(0, 5).map((note) => (
                <button
                  key={note.id}
                  onClick={() => selectNote(note)}
                  className="w-full text-left p-2 hover:bg-hover rounded text-sm flex items-center gap-2 transition-colors duration-fast"
                >
                  <FileText className="h-4 w-4 text-subtle-foreground flex-shrink-0" />
                  <span className="truncate">{note.title}</span>
                </button>
              ))}
            </div>
          </Card>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask AI anything, use @ to mention notes..."
            className="flex-1 focus-smooth"
          />
          <Button 
            onClick={handleSend} 
            disabled={!input.trim()}
            className="px-3"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}