import { FileText, ChevronRight, ChevronDown, Plus, Trash2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  onAddNote: (title: string, parentId?: number) => void;
  onDeleteNote: (noteId: number) => void;
  collapsed: boolean;
}

function NoteItem({ 
  note, 
  selectedNoteId, 
  onSelectNote,
  onAddNote,
  onDeleteNote,
  level = 0,
  creatingSubNote,
  setCreatingSubNote 
}: { 
  note: NoteWithChildren; 
  selectedNoteId: number; 
  onSelectNote: (noteId: number) => void;
  onAddNote: (title: string, parentId?: number) => void;
  onDeleteNote: (noteId: number) => void;
  level?: number;
  creatingSubNote: number | null;
  setCreatingSubNote: (noteId: number | null) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [hovered, setHovered] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const hasChildren = note.children.length > 0;
  const isSelected = note.id === selectedNoteId;

  const handleAddSubNote = () => {
    setCreatingSubNote(note.id);
    setExpanded(true);
  };

  const handleSubmitNewNote = () => {
    if (newNoteTitle.trim()) {
      onAddNote(newNoteTitle.trim(), note.id);
      setNewNoteTitle("");
      setCreatingSubNote(null);
    }
  };

  const handleCancelNewNote = () => {
    setNewNoteTitle("");
    setCreatingSubNote(null);
  };

  return (
    <div>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className="relative group"
      >
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
            <span className="truncate text-sm flex-1">{note.title}</span>
            
            {/* Hover Actions */}
            {hovered && (
              <div className="flex gap-1 ml-auto">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAddSubNote();
                  }}
                  className="h-6 w-6 p-0 hover:bg-secondary-hover"
                >
                  <Plus className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteNote(note.id);
                  }}
                  className="h-6 w-6 p-0 hover:bg-destructive hover:text-destructive-foreground"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            )}
          </div>
        </Button>
      </div>
      
      {hasChildren && expanded && (
        <div>
          {note.children.map((child) => (
            <NoteItem
              key={child.id}
              note={child}
              selectedNoteId={selectedNoteId}
              onSelectNote={onSelectNote}
              onAddNote={onAddNote}
              onDeleteNote={onDeleteNote}
              level={level + 1}
              creatingSubNote={creatingSubNote}
              setCreatingSubNote={setCreatingSubNote}
            />
          ))}
          
          {/* Inline Sub-note Creation */}
          {creatingSubNote === note.id && (
            <div style={{ paddingLeft: `${(level + 1) * 16 + 8}px` }} className="p-2">
              <Input
                value={newNoteTitle}
                onChange={(e) => setNewNoteTitle(e.target.value)}
                placeholder="Enter note title..."
                className="h-8 text-sm"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSubmitNewNote();
                  } else if (e.key === 'Escape') {
                    handleCancelNewNote();
                  }
                }}
                onBlur={handleCancelNewNote}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function FileExplorer({ notes, selectedNoteId, onSelectNote, onAddNote, onDeleteNote, collapsed }: FileExplorerProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const [creatingTopNote, setCreatingTopNote] = useState(false);
  const [creatingSubNote, setCreatingSubNote] = useState<number | null>(null);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  
  if (collapsed) return null;

  const handleAddTopNote = () => {
    setCreatingTopNote(true);
  };

  const handleSubmitTopNote = () => {
    if (newNoteTitle.trim()) {
      onAddNote(newNoteTitle.trim());
      setNewNoteTitle("");
      setCreatingTopNote(false);
    }
  };

  const handleCancelTopNote = () => {
    setNewNoteTitle("");
    setCreatingTopNote(false);
  };

  // Filter notes based on search query
  const filterNotes = (notes: NoteWithChildren[], query: string): NoteWithChildren[] => {
    if (!query.trim()) return notes;
    
    return notes.filter(note => {
      const matchesTitle = note.title.toLowerCase().includes(query.toLowerCase());
      const hasMatchingChildren = filterNotes(note.children, query).length > 0;
      return matchesTitle || hasMatchingChildren;
    }).map(note => ({
      ...note,
      children: filterNotes(note.children, query)
    }));
  };

  const filteredNotes = filterNotes(notes, searchQuery);

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
      
      {/* Search Bar with Add Note Button */}
      <div className="p-3 border-b border-panel-border">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-subtle-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes..."
              className="pl-9 h-8 text-sm"
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAddTopNote}
            className="h-8 w-8 p-0 hover:bg-hover"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {/* Top-level note creation */}
          {creatingTopNote && (
            <div className="p-2">
              <Input
                value={newNoteTitle}
                onChange={(e) => setNewNoteTitle(e.target.value)}
                placeholder="Enter note title..."
                className="h-8 text-sm"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSubmitTopNote();
                  } else if (e.key === 'Escape') {
                    handleCancelTopNote();
                  }
                }}
                onBlur={handleCancelTopNote}
              />
            </div>
          )}
          
          {filteredNotes.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              selectedNoteId={selectedNoteId}
              onSelectNote={onSelectNote}
              onAddNote={onAddNote}
              onDeleteNote={onDeleteNote}
              creatingSubNote={creatingSubNote}
              setCreatingSubNote={setCreatingSubNote}
            />
          ))}
        </div>
      </div>
    </div>
  );
}