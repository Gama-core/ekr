import { useState, useEffect, useRef, useCallback } from "react"; // NEW: Import useCallback
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sparkles, Bold, Italic, List, ListOrdered, Heading1, Heading2, Heading3 } from "lucide-react";
import { AIBlock } from "./AIBlock";
import { useDebounce } from "@/hooks/useDebounce";
import { Note } from "@/lib/api";
import { useToast } from "@/hooks/use-toast"; // NEW: Import useToast for feedback

interface NoteEditorProps {
  note: Note;
  onUpdateNote: (updates: Partial<Note>) => void;
}

export function NoteEditor({ note, onUpdateNote }: NoteEditorProps) {
  const [title, setTitle] = useState(note.title);
  const [text, setText] = useState(note.text);
  const [aiBlock, setAIBlock] = useState<{
    type: 'summary' | 'fact-check' | 'update' | null;
    content: any;
  }>({ type: null, content: null });

  // NEW: Add toast for user feedback
  const { toast } = useToast();

  // NEW: State to track if there are unsaved changes
  const [isDirty, setIsDirty] = useState(false);

  const debouncedTitle = useDebounce(title, 1500); // Increased debounce for better UX
  const debouncedText = useDebounce(text, 1500);

  // This ref is no longer needed for the save logic but is kept for reference
  const isMounting = useRef(true);

  // This effect resets the editor's state ONLY when switching to a different note
  useEffect(() => {
    setTitle(note.title);
    setText(note.text);
    setAIBlock({ type: null, content: null });
    setIsDirty(false); // The newly loaded note is "clean"
    isMounting.current = true;
  }, [note.id]);

  // This is the core save function, now reusable
  const performSave = useCallback(() => {
    if (!isDirty) return; // Don't save if there are no changes

    onUpdateNote({ title, text });
    setIsDirty(false); // Mark as clean immediately after initiating save

    // Provide visual feedback for manual save
    toast({
      title: "Note Saved",
      description: `Changes to "${title}" have been saved.`,
    });
  }, [isDirty, title, text, onUpdateNote, toast]);


  // Auto-save effect for title and text
  useEffect(() => {
    if (isMounting.current) {
      isMounting.current = false;
      return;
    }
    if (isDirty) {
      // We call the same save function, but without the toast for a silent auto-save
      onUpdateNote({ title: debouncedTitle, text: debouncedText });
      setIsDirty(false);
    }
  }, [debouncedTitle, debouncedText]); // Combined for simplicity

  // NEW: Event listener for Ctrl+S
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault(); // Prevent the browser's default save action
        console.log("Ctrl+S pressed, triggering manual save.");
        performSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [performSave]); // Dependency is on the memoized save function


  // MODIFIED: onChange handlers now also mark the note as "dirty"
  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    setIsDirty(true);
  };

  const handleTextChange = (newText: string) => {
    setText(newText);
    setIsDirty(true);
  };

  // ... (insertAtCursor and AI functions remain the same)
  const insertAtCursor = (before: string, after: string = '') => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = text.substring(start, end);
    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);

    handleTextChange(newText); // Use the new handler to set dirty state

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    }, 0);
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-panel-border bg-panel-secondary">
        <div className="flex items-center justify-between gap-4">
          <Input
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)} // MODIFIED
            className="text-lg font-semibold border-none bg-transparent p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
            placeholder="Note title..."
          />
          {/* Dropdown Menu */}
        </div>
      </div>
      <div className="p-3 border-b border-panel-border bg-panel-secondary">
          {/* Toolbar */}
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-4">
          {/* AI Block */}
          <Textarea
            value={text}
            onChange={(e) => handleTextChange(e.target.value)} // MODIFIED
            className="min-h-[600px] border-none bg-transparent p-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed"
            placeholder="Start writing your note..."
          />
        </div>
      </div>
    </div>
  );
}