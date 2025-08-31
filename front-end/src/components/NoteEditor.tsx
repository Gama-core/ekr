import { useState, useEffect, useCallback } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sparkles, Loader2, Eye, Pencil } from "lucide-react";
import { AIBlock } from "./AIBlock";
import { useDebounce } from "@/hooks/useDebounce";
import { api, Note, Correction } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { ScrollArea } from "@/components/ui/scroll-area";

interface NoteEditorProps {
  note: Note;
  onUpdateNote: (updates: Partial<Note>) => void;
  onNoteOverride: () => void;
}

export function NoteEditor({ note, onUpdateNote, onNoteOverride }: NoteEditorProps) {
  const [title, setTitle] = useState(note.title);
  const [text, setText] = useState(note.text);
  const [isDirty, setIsDirty] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  // FIX #1: Default state is now `false` (Preview Mode)
  const [editMode, setEditMode] = useState(false);
  const [aiBlock, setAIBlock] = useState<{
    type: 'summary' | 'fact-check' | 'update' | null;
    content: any;
  }>({ type: null, content: null });

  const { toast } = useToast();
  const debouncedTitle = useDebounce(title, 1000);
  const debouncedText = useDebounce(text, 1000);

  useEffect(() => {
    setTitle(note.title);
    setText(note.text);
    setAIBlock({ type: null, content: null });
    setIsDirty(false);

    // FIX #2 & #3: Default to Preview mode, but switch to Edit mode for new notes.
    const newNoteDefaultText = `# ${note.title}\n\nStart writing your note here...`;
    // If the note text is the default boilerplate, it's a new note, so start in edit mode.
    if (note.text === newNoteDefaultText) {
      setEditMode(true);
    } else {
      setEditMode(false);
    }
  }, [note.id, note.title, note.text]); // Depend on text/title to detect new note content

  const performAutoSave = useCallback(() => {
    if (isDirty) {
      onUpdateNote({ title: debouncedTitle, text: debouncedText });
      setIsDirty(false);
    }
  }, [isDirty, debouncedTitle, debouncedText, onUpdateNote]);

  useEffect(() => {
    const handler = setTimeout(performAutoSave, 1000);
    return () => clearTimeout(handler);
  }, [debouncedTitle, debouncedText, performAutoSave]);

  const handleAIAction = async (action: 'summary' | 'fact-check' | 'update') => {
    setIsAiLoading(true);
    setAIBlock({ type: null, content: null });
    setEditMode(true);
    try {
      if (action === 'summary') {
        const response = await api.summarizeNote(note.id);
        setAIBlock({ type: 'summary', content: response });
      } else if (action === 'fact-check') {
        const response = await api.factCheckNote(note.id);
        if (response.corrections.length === 0) {
            toast({ title: "Fact-Check", description: "No issues found in the note." });
            setAIBlock({ type: null, content: null });
        } else {
            setAIBlock({ type: 'fact-check', content: response });
        }
      } else if (action === 'update') {
        const response = await api.updateNoteAutonomous(note.id);
        setAIBlock({ type: 'update', content: response });
      }
    } catch (error) {
      toast({ title: "AI Error", description: String(error), variant: "destructive" });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleGuidedUpdate = async (corrections: Correction[]) => {
    setIsAiLoading(true);
    try {
      const response = await api.updateNoteGuided(note.id, corrections);
      setAIBlock({ type: 'update', content: response });
    } catch (error) {
      toast({ title: "AI Error", description: String(error), variant: "destructive" });
    } finally {
      setIsAiLoading(false);
    }
  };

  const handleOverrideContent = async (newText: string) => {
    setIsAiLoading(true);
    try {
      await api.overrideNoteContent(note.id, newText);
      setAIBlock({ type: null, content: null });
      onNoteOverride();
      toast({ title: "Success", description: "Note has been updated with AI changes." });
    } catch (error) {
      toast({ title: "Error", description: `Failed to save changes: ${error}`, variant: "destructive" });
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-panel-border bg-panel-secondary flex items-center justify-between gap-4">
        <Input
          value={title}
          onChange={(e) => { setTitle(e.target.value); setIsDirty(true); }}
          className="text-lg font-semibold border-none bg-transparent p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
          placeholder="Note title..."
        />
        <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditMode(!editMode)} className="gap-2">
                {editMode ? <Eye className="h-4 w-4" /> : <Pencil className="h-4 w-4" />}
                {editMode ? "Preview" : "Edit"}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2" disabled={isAiLoading}>
                  {isAiLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-ai-primary" />}
                  AI Tools
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem onSelect={() => handleAIAction('summary')}>Generate Summary</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => handleAIAction('fact-check')}>Fact-Check this Note</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => handleAIAction('update')}>Update with AI</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-4">
          {aiBlock.type && (
            <AIBlock
              type={aiBlock.type}
              content={aiBlock.content}
              onApplyCorrections={handleGuidedUpdate}
              onSaveUpdate={handleOverrideContent}
              onDiscard={() => setAIBlock({ type: null, content: null })}
            />
          )}
          {editMode ? (
              <Textarea
                value={text}
                onChange={(e) => { setText(e.target.value); setIsDirty(true); }}
                className="min-h-[600px] border-none bg-transparent p-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed"
                placeholder="Start writing your note..."
              />
          ) : (
             <article className="prose dark:prose-invert max-w-none min-h-[600px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {text || "Nothing to preview yet."}
                </ReactMarkdown>
             </article>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}