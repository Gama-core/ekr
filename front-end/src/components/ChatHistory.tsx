import { MessageCircle, Clock, MoreVertical, Edit2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useNavigate } from "react-router-dom";

interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
  isActive?: boolean;
}

interface ChatHistoryProps {
  sessions: ChatSession[];
  onSelectSession: (sessionId: string) => void;
  collapsed: boolean;
}

const mockSessions: ChatSession[] = [
  {
    id: '1',
    title: 'Product Strategy Discussion',
    lastMessage: 'Can you help me understand our Q4 product strategy...',
    timestamp: '2 hours ago',
    isActive: true
  },
  {
    id: '2',
    title: 'User Research Analysis',
    lastMessage: 'What are the main pain points from our user research?',
    timestamp: '1 day ago'
  },
  {
    id: '3',
    title: 'Market Competitive Analysis',
    lastMessage: 'Compare our features with competitors',
    timestamp: '3 days ago'
  },
  {
    id: '4',
    title: 'Sprint Planning Help',
    lastMessage: 'Help me prioritize features for next sprint',
    timestamp: '1 week ago'
  },
  {
    id: '5',
    title: 'Technical Documentation',
    lastMessage: 'Generate API documentation for our endpoints',
    timestamp: '2 weeks ago'
  }
];

function ChatSessionItem({ 
  session, 
  onSelect, 
  isSelected 
}: { 
  session: ChatSession; 
  onSelect: () => void;
  isSelected: boolean;
}) {
  const handleRename = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Rename session:', session.id);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Delete session:', session.id);
  };

  return (
    <div className={`
      group relative w-full rounded-sm transition-colors duration-fast
      hover:bg-hover
      ${isSelected ? 'bg-active' : ''}
    `}>
      <Button
        variant="ghost"
        onClick={onSelect}
        className={`
          w-full justify-start text-left p-3 h-auto min-h-[60px] rounded-sm
          hover:bg-transparent
          ${isSelected ? 'text-primary font-medium' : 'text-foreground'}
        `}
      >
        <div className="flex items-start gap-3 w-full min-w-0 pr-8">
          <MessageCircle className="h-4 w-4 flex-shrink-0 text-subtle-foreground mt-1" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{session.title}</p>
            <p className="text-xs text-muted-foreground truncate mt-1">{session.lastMessage}</p>
            <div className="flex items-center gap-1 mt-2">
              <Clock className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">{session.timestamp}</span>
            </div>
          </div>
        </div>
      </Button>
      
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-fast">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 hover:bg-secondary-hover"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreVertical className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={handleRename} className="cursor-pointer">
              <Edit2 className="h-3 w-3 mr-2" />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleDelete} className="cursor-pointer text-destructive focus:text-destructive">
              <Trash2 className="h-3 w-3 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export function ChatHistory({ sessions = mockSessions, onSelectSession, collapsed }: ChatHistoryProps) {
  const navigate = useNavigate();
  
  if (collapsed) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-panel-border">
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-sm"
            onClick={() => navigate('/')}
          >
            Notes
          </Button>
          <Button
            variant="default"
            size="sm"
            className="text-sm"
          >
            ChatBot
          </Button>
        </div>
      </div>
      
      <div className="p-3 border-b border-panel-border">
        <h3 className="text-sm font-medium text-foreground">Chat History</h3>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-1">
          {sessions.map((session) => (
            <ChatSessionItem
              key={session.id}
              session={session}
              onSelect={() => onSelectSession(session.id)}
              isSelected={session.isActive || false}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}