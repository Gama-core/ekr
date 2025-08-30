import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle, MoreVertical, Edit2, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

interface ChatSession {
  id: string;
  title: string;
  lastMessage: string;
  timestamp: string;
}

interface ChatSidebarProps {
  sessions?: ChatSession[];
  onSelectSession: (id: string) => void;
  selectedSessionId?: string;
  onNewChat?: () => void;
}

const mockSessions: ChatSession[] = [
  {
    id: '1',
    title: 'Q4 Product Strategy Discussion',
    lastMessage: 'Can you help me understand our Q4 product strategy...',
    timestamp: '2 hours ago'
  },
  {
    id: '2',
    title: 'User Research Findings Summary',
    lastMessage: 'Based on the latest user interviews...',
    timestamp: '1 day ago'
  },
  {
    id: '3',
    title: 'Market Analysis Report',
    lastMessage: 'The market trends show significant growth...',
    timestamp: '3 days ago'
  },
  {
    id: '4',
    title: 'Competitive Analysis',
    lastMessage: 'Our main competitors are focusing on...',
    timestamp: '1 week ago'
  },
  {
    id: '5',
    title: 'Feature Prioritization',
    lastMessage: 'Let\'s discuss which features should be...',
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
  const [isHovered, setIsHovered] = useState(false);

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
    <SidebarMenuItem>
      <div 
        className={`
          group relative w-full rounded-sm transition-colors duration-fast cursor-pointer
          ${isSelected ? 'bg-accent' : 'hover:bg-muted'}
        `}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={onSelect}
      >
        <SidebarMenuButton asChild className="h-auto p-0">
          <div className="w-full p-3">
            <div className="flex items-start gap-3 w-full min-w-0 pr-8">
              <MessageCircle className="h-4 w-4 flex-shrink-0 text-muted-foreground mt-1" />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${isSelected ? 'text-accent-foreground' : 'text-foreground'}`}>
                  {session.title}
                </p>
              </div>
            </div>
          </div>
        </SidebarMenuButton>
        
        {(isHovered || isSelected) && (
          <div className="absolute top-2 right-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 hover:bg-secondary"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="right" className="w-40 bg-background border border-border shadow-lg z-50">
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
        )}
      </div>
    </SidebarMenuItem>
  );
}

export function ChatSidebar({ 
  sessions = mockSessions, 
  onSelectSession, 
  selectedSessionId = '1',
  onNewChat 
}: ChatSidebarProps) {
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";
  const navigate = useNavigate();

  const handleNewChat = () => {
    console.log('New chat clicked');
    onNewChat?.();
  };

  return (
    <Sidebar className="border-r border-border bg-background">
      <SidebarHeader className="p-4 border-b border-border">
        {/* Navigation Buttons */}
        <div className="flex gap-2 mb-4">
          <Button
            variant="ghost"
            size="sm"
            className="text-sm flex-1"
            onClick={() => navigate('/')}
          >
            Notes
          </Button>
          <Button
            variant="default"
            size="sm"
            className="text-sm flex-1"
          >
            ChatBot
          </Button>
        </div>
        
        {/* New Chat Button */}
        <div className="mt-2">
          <Button 
            onClick={handleNewChat}
            variant="secondary"
            className="w-full justify-start gap-2"
          >
            <Plus className="h-4 w-4" />
            {!isCollapsed && <span>New Chat</span>}
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="px-4 py-2 text-xs font-medium text-muted-foreground">
            {!isCollapsed && "Recent Conversations"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1 px-2">
              {sessions.map((session) => (
                <ChatSessionItem
                  key={session.id}
                  session={session}
                  onSelect={() => onSelectSession(session.id)}
                  isSelected={selectedSessionId === session.id}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}