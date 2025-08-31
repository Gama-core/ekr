// src/components/ChatSidebar.tsx

import { useNavigate } from "react-router-dom";
import { MessageCircle, Plus, MoreVertical, Edit2, Trash2 } from "lucide-react";
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
import { ChatSession } from "@/hooks/useChatHistory";

interface ChatSidebarProps {
  sessions: ChatSession[];
  onSelectSession: (id: string) => void;
  selectedSessionId: string;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void; // Add this required prop
}

function ChatSessionItem({ session, onSelect, isSelected, onDelete }: { session: ChatSession; onSelect: () => void; isSelected: boolean; onDelete: (id: string) => void; }) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent the session from being selected when deleting
    onDelete(session.id);
  };

  return (
    <SidebarMenuItem>
      <div
        className={`group relative w-full rounded-md transition-colors duration-fast cursor-pointer ${isSelected ? 'bg-accent' : 'hover:bg-muted'}`}
        onClick={onSelect}
      >
        <SidebarMenuButton asChild className="h-auto p-0 bg-transparent hover:bg-transparent">
          <div className="w-full p-2">
            <div className="flex items-center gap-3 w-full min-w-0">
              <MessageCircle className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium truncate ${isSelected ? 'text-accent-foreground' : 'text-foreground'}`}>
                  {session.title}
                </p>
              </div>
            </div>
          </div>
        </SidebarMenuButton>
         <div className="absolute top-1/2 -translate-y-1/2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => e.stopPropagation()}>
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="right">
                <DropdownMenuItem onClick={handleDelete} className="text-destructive">
                  <Trash2 className="mr-2 h-4 w-4" />
                  <span>Delete</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
         </div>
      </div>
    </SidebarMenuItem>
  );
}

export function ChatSidebar({ sessions, onSelectSession, selectedSessionId, onNewChat, onDeleteSession }: ChatSidebarProps) {
  const { state } = useSidebar();
  const isCollapsed = state === "collapsed";
  const navigate = useNavigate();

  return (
    <Sidebar className="border-r bg-background">
      <SidebarHeader className="p-4 border-b">
        <div className="flex gap-2 mb-4">
          <Button variant="ghost" size="sm" className="flex-1" onClick={() => navigate('/')}>Notes</Button>
          <Button variant="default" size="sm" className="flex-1">ChatBot</Button>
        </div>
        <Button onClick={onNewChat} variant="secondary" className="w-full justify-start gap-2">
          <Plus className="h-4 w-4" />
          {!isCollapsed && <span>New Chat</span>}
        </Button>
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
                  onDelete={onDeleteSession} // Pass the delete handler down
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}