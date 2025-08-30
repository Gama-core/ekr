import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { ChatSidebar } from "@/components/ChatSidebar";
import { 
  Send, 
  Paperclip, 
  Globe, 
  Bot, 
  User, 
  FileText, 
  File, 
  ChevronDown,
  ChevronUp,
  Sparkles,
  Upload,
  Image,
  FileVideo
} from "lucide-react";

interface Message {
  id: string;
  type: 'user' | 'ai' | 'thinking';
  content: string;
  sources?: Source[];
  thinking?: ThinkingTask[];
}

interface Source {
  type: 'note' | 'file' | 'web';
  title: string;
  snippet: string;
  icon: any;
}

interface ThinkingTask {
  text: string;
  completed: boolean;
}

const mockMessages: Message[] = [
  {
    id: '1',
    type: 'user',
    content: 'Can you help me understand our Q4 product strategy and how it relates to our user research findings?'
  },
  {
    id: '2',
    type: 'thinking',
    content: '',
    thinking: [
      { text: 'Searching your notes...', completed: true },
      { text: 'Reading uploaded files...', completed: true },
      { text: 'Rewriting query for web search...', completed: true },
      { text: 'Searching the web...', completed: true },
      { text: 'Synthesizing answer...', completed: true }
    ]
  },
  {
    id: '3',
    type: 'ai',
    content: `Based on your notes and research, here's a comprehensive overview of your Q4 product strategy:

## Strategic Focus Areas

Your Q4 strategy centers on **user experience improvements** and **market expansion**, directly addressing the pain points identified in your user research:

### Key Objectives
- **25% improvement in user retention** - directly targeting the information overload issue users face
- **Expansion to 3 new markets** - leveraging opportunities in AI-assisted tools
- **AI-powered feature launch** - addressing users' need for better content organization

### Research-Driven Decisions

The strategy aligns perfectly with your user research findings:

1. **Information Overload Solution**: The AI-powered features directly address users struggling with too much information
2. **Search Enhancement**: Plans to improve search functionality based on user feedback about inadequate current search
3. **Mobile Experience**: Market expansion includes mobile-first approach for new markets

This shows a data-driven approach where user pain points directly inform strategic priorities.`,
    sources: [
      {
        type: 'note',
        title: 'Product Strategy',
        snippet: 'This document outlines our comprehensive product strategy for the upcoming quarter. We\'ll focus on user experience improvements and market expansion...',
        icon: FileText
      },
      {
        type: 'note', 
        title: 'User Research Findings',
        snippet: 'Based on our recent user interviews and surveys, we\'ve identified several key insights: Users struggle with information overload...',
        icon: FileText
      },
      {
        type: 'file',
        title: 'Q4_Financials.pdf',
        snippet: 'The quarterly revenue increased by 15% year-over-year, providing budget for strategic initiatives...',
        icon: File
      },
      {
        type: 'web',
        title: 'TechCrunch: AI Market Trends 2025',
        snippet: 'The market for AI-enhanced productivity tools is expected to double, making this an optimal time for expansion...',
        icon: Globe
      }
    ]
  }
];

function MessageBubble({ message }: { message: Message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (message.type === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="flex items-start gap-3 max-w-[80%]">
          <div className="bg-foreground text-background px-4 py-3 rounded-lg">
            <p className="text-sm">{message.content}</p>
          </div>
          <div className="w-8 h-8 bg-foreground rounded-full flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-background" />
          </div>
        </div>
      </div>
    );
  }

  if (message.type === 'thinking') {
    return (
      <div className="flex justify-start mb-4">
        <div className="flex items-start gap-3 max-w-[80%]">
          <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4 text-muted-foreground animate-pulse" />
          </div>
          <div className="bg-muted px-4 py-3 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse"></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse delay-75"></div>
                <div className="w-2 h-2 bg-muted-foreground rounded-full animate-pulse delay-150"></div>
              </div>
              <span className="text-sm text-muted-foreground">AI is thinking...</span>
            </div>
            <div className="space-y-2">
              {message.thinking?.map((task, index) => (
                <div key={index} className="flex items-center gap-2 text-sm">
                  <span className="text-green-600">✓</span>
                  <span className="text-muted-foreground">{task.text}</span>
                </div>
              ))}
            </div>
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
        <div className="bg-muted px-4 py-3 rounded-lg">
          <div className="prose prose-sm max-w-none">
            <div className="whitespace-pre-wrap text-sm">{message.content}</div>
          </div>
          
          {message.sources && message.sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border">
              <Collapsible open={sourcesOpen} onOpenChange={setSourcesOpen}>
                <CollapsibleTrigger asChild>
                  <Button variant="ghost" size="sm" className="p-0 h-auto font-medium text-xs">
                    Sources Used ({message.sources.length})
                    {sourcesOpen ? (
                      <ChevronUp className="w-3 h-3 ml-1" />
                    ) : (
                      <ChevronDown className="w-3 h-3 ml-1" />
                    )}
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="space-y-2">
                    {message.sources.map((source, index) => {
                      const IconComponent = source.icon;
                      return (
                        <div key={index} className="flex gap-2 p-2 bg-background rounded border border-border">
                          <IconComponent className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-xs text-foreground">{source.title}</p>
                            <p className="text-xs text-muted-foreground truncate">{source.snippet}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
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
  const [message, setMessage] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [messages] = useState<Message[]>(mockMessages);
  const [selectedSessionId, setSelectedSessionId] = useState('1');

  const handleSend = () => {
    if (!message.trim()) return;
    // Handle sending message
    setMessage('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = (type: string) => {
    console.log(`Upload ${type} file`);
    // Handle file upload logic here
  };

  const handleSelectSession = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    console.log('Selected session:', sessionId);
  };

  const handleNewChat = () => {
    console.log('Starting new chat');
    // Handle new chat logic here
  };

  return (
    <SidebarProvider>
      <div className="h-screen flex w-full bg-background overflow-hidden">
        <ChatSidebar 
          onSelectSession={handleSelectSession}
          selectedSessionId={selectedSessionId}
          onNewChat={handleNewChat}
        />

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <header className="border-b border-border bg-background px-6 py-4 flex items-center gap-2">
            <SidebarTrigger />
            <h1 className="text-xl font-semibold text-foreground">AI Chatbot</h1>
          </header>

          {/* Chat History Area */}
          <div className="flex-1 overflow-hidden">
            <ScrollArea className="h-full">
              <div className="max-w-4xl mx-auto px-6 py-6">
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Chat Input Area */}
          <div className="border-t border-border bg-background">
            <div className="max-w-4xl mx-auto px-6 py-4">
              {/* Web Search Toggle */}
              <div className="flex items-center gap-2 mb-3">
                <Globe className="w-4 h-4 text-muted-foreground" />
                <label htmlFor="web-search" className="text-sm text-foreground">
                  Web Search
                </label>
                <Switch
                  id="web-search"
                  checked={webSearchEnabled}
                  onCheckedChange={setWebSearchEnabled}
                />
              </div>

              {/* Input Row */}
              <div className="flex items-end gap-2">
                {/* File Upload Button */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="icon" className="flex-shrink-0">
                      <Paperclip className="w-4 h-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-48 bg-background border border-border shadow-lg z-50">
                    <DropdownMenuItem onClick={() => handleFileUpload('document')} className="cursor-pointer">
                      <FileText className="h-4 w-4 mr-2" />
                      Upload Document
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFileUpload('image')} className="cursor-pointer">
                      <Image className="h-4 w-4 mr-2" />
                      Upload Image
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFileUpload('video')} className="cursor-pointer">
                      <FileVideo className="h-4 w-4 mr-2" />
                      Upload Video
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFileUpload('any')} className="cursor-pointer">
                      <Upload className="h-4 w-4 mr-2" />
                      Upload Any File
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Text Input */}
                <div className="flex-1">
                  <Textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Ask a question, upload a file, or toggle web search..."
                    className="min-h-[44px] max-h-32 resize-none"
                    rows={1}
                  />
                </div>

                {/* Send Button */}
                <Button
                  onClick={handleSend}
                  disabled={!message.trim()}
                  size="icon"
                  className="flex-shrink-0"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SidebarProvider>
  );
}