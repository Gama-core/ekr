import { FileText, ChevronRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

interface NoteWithChildren {
  id: number;
  parent_id: number | null;
  title: string;
  text: string;
  children: NoteWithChildren[];
}

interface FileExplorerProps {
  notes: NoteWithChildren[];
  selectedNoteId: number;
  onSelectNote: (noteId: number) => void;
  collapsed: boolean;
}

function NoteItem({ 
  note, 
  selectedNoteId, 
  onSelectNote, 
  level = 0 
}: { 
  note: NoteWithChildren; 
  selectedNoteId: number; 
  onSelectNote: (noteId: number) => void;
  level?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = note.children.length > 0;
  const isSelected = note.id === selectedNoteId;

  return (
    <div>
      <Button
        variant="ghost"
        onClick={() => onSelectNote(note.id)}
        className={`
          w-full justify-start text-left p-2 h-auto min-h-[36px] rounded-sm
          hover:bg-hover transition-colors duration-fast
          ${isSelected ? 'bg-active text-primary font-medium' : 'text-foreground'}
        `}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        <div className="flex items-center gap-2 w-full min-w-0">
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(!expanded);
              }}
              className="p-0.5 hover:bg-secondary-hover rounded transition-colors duration-fast"
            >
              {expanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
            </button>
          )}
          {!hasChildren && <div className="w-4" />}
          
          <FileText className="h-4 w-4 flex-shrink-0 text-subtle-foreground" />
          <span className="truncate text-sm">{note.title}</span>
        </div>
      </Button>
      
      {hasChildren && expanded && (
        <div>
          {note.children.map((child) => (
            <NoteItem
              key={child.id}
              note={child}
              selectedNoteId={selectedNoteId}
              onSelectNote={onSelectNote}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileExplorer({ notes, selectedNoteId, onSelectNote, collapsed }: FileExplorerProps) {
  const navigate = useNavigate();
  const location = useLocation();
  
  if (collapsed) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-panel-border">
        <div className="flex gap-2">
          <Button
            variant={location.pathname === '/' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => navigate('/')}
            className="text-sm"
          >
            Notes
          </Button>
          <Button
            variant={location.pathname === '/chatbot' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => navigate('/chatbot')}
            className="text-sm"
          >
            ChatBot
          </Button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {notes.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              selectedNoteId={selectedNoteId}
              onSelectNote={onSelectNote}
            />
          ))}
        </div>
      </div>
    </div>
  );
}