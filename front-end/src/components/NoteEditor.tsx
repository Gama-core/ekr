import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sparkles, Bold, Italic, List, ListOrdered, Heading1, Heading2, Heading3 } from "lucide-react";
import { AIBlock } from "./AIBlock";
import { useDebounce } from "@/hooks/useDebounce";
import { Note } from "@/lib/api";

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

  const debouncedTitle = useDebounce(title, 500);
  const debouncedText = useDebounce(text, 500);

  // Effect for saving title changes
  useEffect(() => {
    // Only call update if the debounced title is different from the original prop title
    if (debouncedTitle !== note.title) {
        onUpdateNote({ title: debouncedTitle });
    }
  }, [debouncedTitle]); // Dependency is only on the debounced value

  // Effect for saving text changes
  useEffect(() => {
    // Only call update if the debounced text is different from the original prop text
    if (debouncedText !== note.text) {
        onUpdateNote({ text: debouncedText });
    }
  }, [debouncedText]); // Dependency is only on the debounced value


  // --- THIS IS THE KEY FIX ---
  // This effect now ONLY runs when the user clicks on a DIFFERENT note.
  // It no longer depends on the `note` object reference, which prevents it
  // from resetting the user's typing when the parent component re-renders.
  useEffect(() => {
    setTitle(note.title);
    setText(note.text);
    setAIBlock({ type: null, content: null });
  }, [note.id]); // Only reset when switching to a different note


  const insertAtCursor = (before: string, after: string = '') => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = text.substring(start, end);
    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);

    setText(newText);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    }, 0);
  };

  const handleAIAction = (action: string) => {
    // AI action logic remains the same...
  };

  const handleApplyCorrections = () => {
    // Correction logic remains the same...
  };

  const handleSaveUpdate = () => {
    // Save update logic remains the same...
  };

  const handleDiscardAI = () => {
    // Discard AI logic remains the same...
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-panel-border bg-panel-secondary">
        <div className="flex items-center justify-between gap-4">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="text-lg font-semibold border-none bg-transparent p-0 h-auto focus-visible:ring-0 focus-visible:ring-offset-0"
            placeholder="Note title..."
          />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-2 ai-glow">
                <Sparkles className="h-4 w-4 text-ai-primary" />
                AI Tools
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onClick={() => handleAIAction('summary')}>
                <Sparkles className="h-4 w-4 mr-2 text-ai-primary" />
                Generate Summary
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleAIAction('fact-check')}>
                <Sparkles className="h-4 w-4 mr-2 text-ai-primary" />
                Fact-Check this Note
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleAIAction('update')}>
                <Sparkles className="h-4 w-4 mr-2 text-ai-primary" />
                Update with AI
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Toolbar */}
      <div className="p-3 border-b border-panel-border bg-panel-secondary">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('**', '**')}
            className="h-8 w-8 p-0"
          >
            <Bold className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('*', '*')}
            className="h-8 w-8 p-0"
          >
            <Italic className="h-4 w-4" />
          </Button>
          <div className="w-px h-6 bg-panel-border mx-1" />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('# ', '')}
            className="h-8 w-8 p-0"
          >
            <Heading1 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('## ', '')}
            className="h-8 w-8 p-0"
          >
            <Heading2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('### ', '')}
            className="h-8 w-8 p-0"
          >
            <Heading3 className="h-4 w-4" />
          </Button>
          <div className="w-px h-6 bg-panel-border mx-1" />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('- ', '')}
            className="h-8 w-8 p-0"
          >
            <List className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => insertAtCursor('1. ', '')}
            className="h-8 w-8 p-0"
          >
            <ListOrdered className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 space-y-4">
          {aiBlock.type && (
            <AIBlock
              type={aiBlock.type}
              content={aiBlock.content}
              onApplyCorrections={handleApplyCorrections}
              onSaveUpdate={handleSaveUpdate}
              onDiscard={handleDiscardAI}
            />
          )}

          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="min-h-[600px] border-none bg-transparent p-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed"
            placeholder="Start writing your note..."
          />
        </div>
      </div>
    </div>
  );
}