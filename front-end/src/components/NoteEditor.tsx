import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sparkles, Bold, Italic, List, ListOrdered, Heading1, Heading2, Heading3 } from "lucide-react";
import { AIBlock } from "./AIBlock";

interface Note {
  id: number;
  parent_id: number | null;
  title: string;
  text: string;
}

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

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    onUpdateNote({ title: newTitle });
  };

  const handleTextChange = (newText: string) => {
    setText(newText);
    onUpdateNote({ text: newText });
  };

  const insertAtCursor = (before: string, after: string = '') => {
    const textarea = document.querySelector('textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = text.substring(start, end);
    const newText = text.substring(0, start) + before + selectedText + after + text.substring(end);
    
    setText(newText);
    onUpdateNote({ text: newText });
    
    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, start + before.length + selectedText.length);
    }, 0);
  };

  const handleAIAction = (action: string) => {
    switch (action) {
      case 'summary':
        setAIBlock({
          type: 'summary',
          content: {
            summary_text: "This document outlines a comprehensive product strategy focusing on user experience improvements, market expansion, and AI-powered features. Key objectives include improving user retention by 25%, expanding to 3 new markets, and conducting thorough market analysis to identify opportunities in the AI-enhanced productivity tools sector."
          }
        });
        break;
      case 'fact-check':
        setAIBlock({
          type: 'fact-check',
          content: {
            corrections: [
              {
                note_id: note.id,
                inaccurate_quote: "improve user retention by 25%",
                suggested_correction: "improve user retention by 20% (based on industry benchmarks for SaaS products)"
              },
              {
                note_id: note.id,
                inaccurate_quote: "expand to 3 new markets",
                suggested_correction: "expand to 2 new markets (more realistic given current resources and timeline)"
              }
            ]
          }
        });
        break;
      case 'update':
        setAIBlock({
          type: 'update',
          content: {
            updated_text: "# Enhanced Product Strategy\n\nThis document presents our refined product strategy for Q2 2024, emphasizing user-centric improvements and strategic market expansion.\n\n## Primary Objectives\n\n- **User Retention**: Achieve 20% improvement through enhanced onboarding and feature adoption\n- **Market Expansion**: Strategic entry into 2 high-potential markets with strong demand signals\n- **AI Integration**: Deploy intelligent features that reduce user cognitive load by 30%\n\n## Strategic Market Analysis\n\nThe productivity tools market shows unprecedented growth in AI-enhanced solutions. Our analysis indicates strong demand for:\n\n- Contextual AI assistance\n- Automated content organization\n- Predictive workflow optimization\n\n## Implementation Roadmap\n\n### Phase 1: Foundation (Months 1-2)\n- Enhanced user onboarding experience\n- Core AI feature development\n- Market research and validation\n\n### Phase 2: Expansion (Months 3-4)\n- Launch in primary target market\n- Feature refinement based on user feedback\n- Partnership development\n\n### Phase 3: Scale (Months 5-6)\n- Second market entry\n- Advanced AI capabilities\n- Performance optimization\n\n## Success Metrics\n\n- User retention rate: 20% improvement\n- Market penetration: 15% market share in new regions\n- Feature adoption: 75% of users engaging with AI features\n- Customer satisfaction: NPS score above 50",
            changes: ["Enhanced structure and clarity", "Added implementation roadmap", "Included specific success metrics"]
          }
        });
        break;
    }
  };

  const handleApplyCorrections = () => {
    // Apply fact-check corrections to the text
    let updatedText = text;
    if (aiBlock.type === 'fact-check' && aiBlock.content.corrections) {
      aiBlock.content.corrections.forEach((correction: any) => {
        updatedText = updatedText.replace(correction.inaccurate_quote, correction.suggested_correction);
      });
    }
    setText(updatedText);
    onUpdateNote({ text: updatedText });
    setAIBlock({ type: null, content: null });
  };

  const handleSaveUpdate = () => {
    if (aiBlock.type === 'update' && aiBlock.content.updated_text) {
      setText(aiBlock.content.updated_text);
      onUpdateNote({ text: aiBlock.content.updated_text });
    }
    setAIBlock({ type: null, content: null });
  };

  const handleDiscardAI = () => {
    setAIBlock({ type: null, content: null });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-panel-border bg-panel-secondary">
        <div className="flex items-center justify-between gap-4">
          <Input
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
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
          {/* AI Block */}
          {aiBlock.type && (
            <AIBlock
              type={aiBlock.type}
              content={aiBlock.content}
              onApplyCorrections={handleApplyCorrections}
              onSaveUpdate={handleSaveUpdate}
              onDiscard={handleDiscardAI}
            />
          )}

          {/* Text Editor */}
          <Textarea
            value={text}
            onChange={(e) => handleTextChange(e.target.value)}
            className="min-h-[600px] border-none bg-transparent p-0 resize-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed"
            placeholder="Start writing your note..."
          />
        </div>
      </div>
    </div>
  );
}