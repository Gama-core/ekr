import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sparkles, Loader2 } from "lucide-react";
import { AIBlock } from "./AIBlock";
import { useDebounce } from "@/hooks/useDebounce";
import { api, Note, Correction } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface NoteEditorProps {
  note: Note;
  onUpdateNote: (updates: Partial<Note>) => void;
  onNoteOverride: () => void; // Function to trigger a full refresh
}

export function NoteEditor({ note, onUpdateNote, onNoteOverride }: NoteEditorProps) {
  const [title, setTitle] = useState(note.title);
  const [text, setText] = useState(note.text);
  const [isDirty, setIsDirty] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
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
  }, [note.id]);

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
      onNoteOverride(); // Trigger refresh from parent
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2" disabled={isAiLoading}>
              {isAiLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4 text-ai-primary" />
              )}
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

      <div className="flex-1 overflow-y-auto">
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
          <Textarea
            value={text}
            onChange={(e) => { setText(e.target.value); setIsDirty(true); }}
            className="min-h-[600px] border-none bg-transparent p-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed"
            placeholder="Start writing your note..."
          />
        </div>
      </div>
    </div>
  );
}