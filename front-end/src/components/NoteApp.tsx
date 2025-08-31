import { useState, useEffect } from "react";
import { FileExplorer } from "./FileExplorer";
import { NoteEditor } from "./NoteEditor";
import { AIAssistant } from "./AIAssistant";
import { Button } from "@/components/ui/button";
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { api, Note } from "@/lib/api"; // Import the new api utility and Note type
import { useToast } from "@/hooks/use-toast"; // For showing notifications

export function NoteApp() {
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  const fetchNotes = async () => {
    try {
      setIsLoading(true);
      const fetchedNotes = await api.getNotes();
      setNotes(fetchedNotes);
      if (fetchedNotes.length > 0 && selectedNoteId === null) {
        setSelectedNoteId(fetchedNotes[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch notes:", error);
      toast({
        title: "Error",
        description: "Could not fetch your notes. Please try again later.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, []);

  const selectedNote = notes.find(note => note.id === selectedNoteId);

  const updateNote = async (noteId: number, updates: Partial<Note>) => {
    try {
      const updatedNote = await api.updateNote(noteId, updates);
      setNotes(prev => prev.map(note =>
        note.id === noteId ? updatedNote : note
      ));
    } catch (error) {
      console.error(`Failed to update note ${noteId}:`, error);
      toast({
        title: "Error",
        description: "Failed to save changes.",
        variant: "destructive",
      });
    }
  };

  const addNote = async (title: string, parentId?: number) => {
    try {
        const newNoteData = { title, parent_id: parentId || null, text: `# ${title}\n\nStart writing your note here...` };
        const newNote = await api.createNote(newNoteData);
        setNotes(prev => [...prev, newNote]);
        setSelectedNoteId(newNote.id);
        toast({
            title: "Success",
            description: `Note "${title}" created.`,
        });
    } catch (error) {
        console.error("Failed to create note:", error);
        toast({
            title: "Error",
            description: "Could not create the note.",
            variant: "destructive",
        });
    }
  };

  const deleteNote = async (noteId: number) => {
    const getDescendantIds = (parentId: number): number[] => {
      const children = notes.filter(note => note.parent_id === parentId);
      let descendants = children.map(child => child.id);
      children.forEach(child => {
        descendants = [...descendants, ...getDescendantIds(child.id)];
      });
      return descendants;
    };
    const idsToDelete = [noteId, ...getDescendantIds(noteId)];

    try {
        await api.deleteNote(noteId);
        const remainingNotes = notes.filter(note => !idsToDelete.includes(note.id));
        setNotes(remainingNotes);

        if (idsToDelete.includes(selectedNoteId!)) {
            setSelectedNoteId(remainingNotes.length > 0 ? remainingNotes[0].id : null);
        }
        toast({
            title: "Success",
            description: "Note and its sub-notes deleted.",
        });
    } catch (error) {
        console.error(`Failed to delete note ${noteId}:`, error);
        toast({
            title: "Error",
            description: "Could not delete the note.",
            variant: "destructive",
        });
    }
  };

  const buildNoteTree = (notesToBuild: Note[]) => {
    interface NoteWithChildren extends Note {
      children: NoteWithChildren[];
    }

    const noteMap = new Map(notesToBuild.map(note => [note.id, { ...note, children: [] as NoteWithChildren[] }]));
    const rootNotes: NoteWithChildren[] = [];

    notesToBuild.forEach(note => {
      const noteWithChildren = noteMap.get(note.id)!;
      if (note.parent_id === null) {
        rootNotes.push(noteWithChildren);
      } else {
        const parent = noteMap.get(note.parent_id);
        if (parent) {
          parent.children.push(noteWithChildren);
        }
      }
    });

    return rootNotes;
  };

  return (
    <div className="h-screen flex bg-background overflow-hidden">
      {/* Left Panel - File Explorer */}
      <div className={`
        ${leftPanelCollapsed ? 'w-0' : 'w-80'} 
        transition-all duration-normal border-r border-panel-border bg-panel-primary
        ${leftPanelCollapsed ? 'overflow-hidden' : 'overflow-visible'}
      `}>
        <FileExplorer
          notes={buildNoteTree(notes)}
          selectedNoteId={selectedNoteId!}
          onSelectNote={setSelectedNoteId}
          onAddNote={addNote}
          onDeleteNote={deleteNote}
          collapsed={leftPanelCollapsed}
        />
      </div>

      {/* Left Panel Toggle */}
      <div className="flex flex-col">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
          className="h-8 w-8 p-0 m-2 hover:bg-hover"
        >
          {leftPanelCollapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Center Panel - Note Editor */}
      <div className="flex-1 flex flex-col min-w-0 bg-panel-secondary">
        {isLoading && <div className="p-6">Loading notes...</div>}
        {!isLoading && selectedNote ? (
          <NoteEditor
            key={selectedNote.id}
            note={selectedNote}
            onUpdateNote={(updates) => updateNote(selectedNote.id, updates)}
          />
        ) : (
          !isLoading && <div className="p-6">Select a note to start editing or create a new one.</div>
        )}
      </div>

      {/* Right Panel Toggle */}
      <div className="flex flex-col">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
          className="h-8 w-8 p-0 m-2 hover:bg-hover"
        >
          {rightPanelCollapsed ? (
            <PanelRightOpen className="h-4 w-4" />
          ) : (
            <PanelRightClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Right Panel - AI Assistant */}
      <div className={`
        ${rightPanelCollapsed ? 'w-0' : 'w-80'} 
        transition-all duration-normal border-l border-panel-border bg-panel-primary
        ${rightPanelCollapsed ? 'overflow-hidden' : 'overflow-visible'}
      `}>
        <AIAssistant
          currentNote={selectedNote}
          allNotes={notes}
          collapsed={rightPanelCollapsed}
        />
      </div>
    </div>
  );
}