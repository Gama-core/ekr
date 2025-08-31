import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ChatSidebar } from "@/components/ChatSidebar";
import { api, ChatMessage, Source } from "@/lib/api";
import { useChatHistory } from "@/hooks/useChatHistory";
import { useToast } from "@/hooks/use-toast";
import { Send, Paperclip, Globe, Bot, User, FileText, ChevronDown, ChevronUp, Sparkles, X, Check } from "lucide-react";

// Export this type for the useChatHistory hook
export interface Message extends ChatMessage {
  id: string;
  type: 'user' | 'assistant'; // Role is mapped to type
  sources?: Source[];
}

interface ThinkingTask {
    text: string;
    completed: boolean;
}

function ThinkingBubble({ tasks }: { tasks: ThinkingTask[] }) {
    return (
        <div className="flex justify-start mb-4">
            <div className="flex items-start gap-3 max-w-[80%]">
                <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-muted-foreground animate-pulse" />
                </div>
                <div className="bg-muted px-4 py-3 rounded-lg w-full">
                    <div className="flex items-center gap-2 mb-3">
                        <div className="flex gap-1">
                            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse"></div>
                            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse [animation-delay:0.2s]"></div>
                            <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse [animation-delay:0.4s]"></div>
                        </div>
                        <span className="text-sm text-muted-foreground">AI is thinking...</span>
                    </div>
                    <div className="space-y-2">
                        {tasks.map((task, index) => (
                            <div key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
                                {task.completed ? <Check className="w-4 h-4 text-green-500" /> : <Sparkles className="w-4 h-4 animate-pulse" />}
                                <span>{task.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function MessageBubble({ message }: { message: Message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (message.type === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="flex items-start gap-3 max-w-[80%]">
          <div className="bg-foreground text-background px-4 py-3 rounded-lg">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
          <div className="w-8 h-8 bg-foreground rounded-full flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-background" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-[80%]">
        <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="bg-muted px-4 py-3 rounded-lg w-full">
          <div className="prose prose-sm max-w-none text-foreground">
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          </div>

          {message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border">
              <Collapsible open={sourcesOpen} onOpenChange={setSourcesOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="p-0 h-auto font-medium text-xs text-muted-foreground hover:text-foreground">
                    Sources ({message.sources.length})
                    {sourcesOpen ? <ChevronUp className="w-3 h-3 ml-1" /> : <ChevronDown className="w-3 h-3 ml-1" />}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 space-y-2">
                    {message.sources.map((source, index) => (
                        <div key={index} className="flex gap-2 p-2 bg-background rounded border">
                            <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                            <div>
                                <p className="font-medium text-xs text-foreground">{source.title}</p>
                                <p className="text-xs text-muted-foreground truncate">{source.content_snippet}</p>
                            </div>
                        </div>
                    ))}
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Chatbot() {
  const { toast } = useToast();
  const { sessions, activeSession, activeSessionId, setActiveSessionId, startNewSession, updateSessionMessages, deleteSession } = useChatHistory();

  const [query, setQuery] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingTasks, setThinkingTasks] = useState<ThinkingTask[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollViewportRef.current) {
        scrollViewportRef.current.scrollTo({ top: scrollViewportRef.current.scrollHeight, behavior: 'smooth' });
    }
  }, [activeSession?.messages, isLoading]);

  const handleSend = async () => {
    if (!query.trim() || !activeSessionId) return;

    const userMessage: Message = { id: `msg_${Date.now()}`, type: 'user', role: 'user', content: query };
    const currentMessages = activeSession?.messages ? [...activeSession.messages, userMessage] : [userMessage];
    updateSessionMessages(activeSessionId, currentMessages);

    const queryToSend = query;
    const filesToSend = [...attachedFiles];
    setQuery('');
    setAttachedFiles([]);
    setIsLoading(true);

    const initialTasks = [{ text: "Analyzing your notes...", completed: false }];
    if (filesToSend.length > 0) initialTasks.push({ text: `Reading ${filesToSend.length} file(s)...`, completed: false });
    if (webSearchEnabled) {
      initialTasks.push({ text: "Rewriting query for web...", completed: false });
      initialTasks.push({ text: "Searching the web...", completed: false });
    }
    initialTasks.push({ text: "Synthesizing answer...", completed: false });
    setThinkingTasks(initialTasks);

    try {
      const history = currentMessages.slice(0, -1).map(({ role, content }) => ({ role, content }));
      const response = await api.handleChatRequest(queryToSend, history, webSearchEnabled, filesToSend);

      const aiMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        type: 'assistant',
        role: 'assistant',
        content: response.answer,
        sources: response.sources
      };

      setThinkingTasks(tasks => tasks.map(t => ({ ...t, completed: true })));
      updateSessionMessages(activeSessionId, [...currentMessages, aiMessage]);

    } catch (error) {
      toast({ title: "API Error", description: String(error), variant: "destructive" });
      updateSessionMessages(activeSessionId, activeSession?.messages || []);
    } finally {
      setIsLoading(false);
      setThinkingTasks([]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setAttachedFiles(prev => [...prev, ...Array.from(event.target.files!)]);
    }
  };

  return (
    <SidebarProvider>
      <div className="h-screen flex w-full bg-background overflow-hidden">
        <ChatSidebar
          sessions={sessions}
          onSelectSession={setActiveSessionId}
          selectedSessionId={activeSessionId || ''}
          onNewChat={startNewSession}
          onDeleteSession={deleteSession}
        />

        <main className="flex-1 flex flex-col">
          <header className="border-b bg-background px-6 py-4 flex items-center gap-2">
            <SidebarTrigger />
            <h1 className="text-xl font-semibold text-foreground">{activeSession?.title || 'Chat'}</h1>
          </header>

          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full" viewportRef={scrollViewportRef}>
              <div className="max-w-4xl mx-auto px-6 py-6">
                {activeSession?.messages.map((message) => <MessageBubble key={message.id} message={message} />)}
                {isLoading && <ThinkingBubble tasks={thinkingTasks} />}
              </div>
            </ScrollArea>
          </div>

          <div className="border-t bg-background">
            <div className="max-w-4xl mx-auto px-6 py-4 space-y-3">
               {attachedFiles.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {attachedFiles.map((file, i) => (
                    <div key={i} className="flex items-center gap-2 bg-muted px-2 py-1 rounded-md text-sm">
                      <FileText className="h-4 w-4" /> {file.name}
                      <button onClick={() => setAttachedFiles(files => files.filter((_, index) => index !== i))}>
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-muted-foreground" />
                <label htmlFor="web-search" className="text-sm font-medium">Web Search</label>
                <Switch id="web-search" checked={webSearchEnabled} onCheckedChange={setWebSearchEnabled} />
              </div>

              <div className="flex items-end gap-2">
                <Button variant="outline" size="icon" onClick={() => fileInputRef.current?.click()}>
                  <Paperclip className="w-4 w-4" />
                </Button>
                <input type="file" ref={fileInputRef} onChange={handleFileChange} multiple className="hidden" />

                <Textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question..."
                  className="min-h-[44px] max-h-32 resize-none"
                  rows={1}
                  disabled={isLoading}
                />
                <Button onClick={handleSend} disabled={isLoading || !query.trim()} size="icon">
                  <Send className="w-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}