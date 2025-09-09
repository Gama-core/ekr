// src/components/NoteApp.tsx
import { useState, useEffect } from "react";
import { FileExplorer } from "./FileExplorer";
import { NoteEditor } from "./NoteEditor";
import { AIAssistant } from "./AIAssistant";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { api, Note } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface NoteWithChildren extends Note {
  children: NoteWithChildren[];
}

export function NoteApp() {
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const [noteToDelete, setNoteToDelete] = useState<Note | null>(null);

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

  const buildNoteTree = (notesToBuild: Note[]): NoteWithChildren[] => {
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

  // FIX: Replaced the updateNote function to include the note version in the payload.
  const updateNote = async (noteId: number, updates: Partial<Note>) => {
    try {
      const currentNote = notes.find(n => n.id === noteId);
      if (!currentNote) {
        throw new Error(`Note with id ${noteId} not found in current state.`);
      }

      // Create the payload including the current version for optimistic locking
      const updatePayload = {
        ...updates,
        version: currentNote.version,
      };

      const updatedNote = await api.updateNote(noteId, updatePayload);

      // Update the local state with the new note data from the server
      setNotes(prev => prev.map(note =>
        note.id === noteId ? updatedNote : note
      ));

    } catch (error) {
      console.error(`Failed to update note ${noteId}:`, error);
      toast({
        title: "Error Saving Note",
        description: String(error),
        variant: "destructive",
      });
      // Optional: Refetch notes to sync with server state if an update fails
      // fetchNotes();
    }
  };

  const addNote = async (title: string, parentId?: number) => {
      try {
          const newNoteData = { title, parent_id: parentId || null, text: `# ${title}\n\nStart writing your note here...` };
          const newNote = await api.createNote(newNoteData as any);
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

  const requestDeleteNote = (noteId: number) => {
    const note = notes.find(n => n.id === noteId);
    if (note) {
      setNoteToDelete(note);
    }
  };

  const handleConfirmDelete = async () => {
    if (!noteToDelete) return;

    const getDescendantIds = (parentId: number): number[] => {
      const children = notes.filter(note => note.parent_id === parentId);
      let descendants = children.map(child => child.id);
      children.forEach(child => {
        descendants = [...descendants, ...getDescendantIds(child.id)];
      });
      return descendants;
    };
    const idsToDelete = [noteToDelete.id, ...getDescendantIds(noteToDelete.id)];

    try {
        await api.deleteNote(noteToDelete.id);
        const remainingNotes = notes.filter(note => !idsToDelete.includes(note.id));
        setNotes(remainingNotes);

        if (selectedNoteId !== null && idsToDelete.includes(selectedNoteId)) {
            setSelectedNoteId(remainingNotes.length > 0 ? remainingNotes[0].id : null);
        }
        toast({
            title: "Success",
            description: `Note "${noteToDelete.title}" was deleted.`,
        });
    } catch (error) {
        console.error(`Failed to delete note ${noteToDelete.id}:`, error);
        toast({
            title: "Error",
            description: "Could not delete the note.",
            variant: "destructive",
        });
    } finally {
      setNoteToDelete(null);
    }
  };

  return (
    <>
      <div className="h-screen flex bg-background overflow-hidden">
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
            onDeleteNote={requestDeleteNote}
            collapsed={leftPanelCollapsed}
          />
        </div>

        <div className="flex flex-col">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLeftPanelCollapsed(!leftPanelCollapsed)}
              className="h-8 w-8 p-0 m-2 hover:bg-hover"
            >
              {leftPanelCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </Button>
        </div>

        <div className="flex-1 flex flex-col min-w-0 bg-panel-secondary">
          {isLoading && <div className="p-6">Loading notes...</div>}
          {!isLoading && selectedNote ? (
            <NoteEditor
              key={selectedNote.id}
              note={selectedNote}
              onUpdateNote={(updates) => updateNote(selectedNote.id, updates)}
              onNoteOverride={fetchNotes}
            />
          ) : (
            !isLoading && <div className="p-6">Select a note to start editing or create a new one.</div>
          )}
        </div>

        <div className="flex flex-col">
          <Button
              variant="ghost"
              size="sm"
              onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
              className="h-8 w-8 p-0 m-2 hover:bg-hover"
            >
              {rightPanelCollapsed ? <PanelRightOpen className="h-4 w-4" /> : <PanelRightClose className="h-4 w-4" />}
            </Button>
        </div>

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

      <AlertDialog open={noteToDelete !== null} onOpenChange={() => setNoteToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure you want to delete "{noteToDelete?.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the note and all of its sub-notes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setNoteToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}