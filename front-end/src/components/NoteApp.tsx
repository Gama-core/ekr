import { useState } from "react";
import { FileExplorer } from "./FileExplorer";
import { NoteEditor } from "./NoteEditor";
import { AIAssistant } from "./AIAssistant";
import { Button } from "@/components/ui/button";
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";

interface Note {
  id: number;
  parent_id: number | null;
  title: string;
  text: string;
}

const mockNotes: Note[] = [
  {
    id: 1,
    parent_id: null,
    title: "Product Strategy",
    text: "# Product Strategy\n\nThis document outlines our comprehensive product strategy for the upcoming quarter. We'll focus on user experience improvements and market expansion.\n\n## Key Objectives\n\n- Improve user retention by 25%\n- Expand to 3 new markets\n- Launch AI-powered features\n\n## Market Analysis\n\nThe current market shows strong demand for AI-enhanced productivity tools...",
  },
  {
    id: 2,
    parent_id: 1,
    title: "User Research Findings",
    text: "# User Research Findings\n\nBased on our recent user interviews and surveys, we've identified several key insights:\n\n## Pain Points\n\n- Users struggle with information overload\n- Current search functionality is inadequate\n- Mobile experience needs improvement\n\n## Opportunities\n\n- AI-assisted content organization\n- Smart notifications\n- Enhanced collaboration features",
  },
  {
    id: 3,
    parent_id: 1,
    title: "Competitive Analysis",
    text: "# Competitive Analysis\n\nAnalysis of top competitors in the productivity space:\n\n## Notion\n- Strengths: Flexible workspace, good collaboration\n- Weaknesses: Steep learning curve, performance issues\n\n## Obsidian\n- Strengths: Powerful linking, local storage\n- Weaknesses: Complex for casual users",
  },
  {
    id: 4,
    parent_id: null,
    title: "Meeting Notes",
    text: "# Weekly Team Meeting\n\n**Date:** March 15, 2024\n**Attendees:** Sarah, Mike, Alex, Emma\n\n## Agenda Items\n\n1. Sprint Review\n2. Q1 Goals Discussion\n3. New Feature Proposals\n\n## Action Items\n\n- [ ] Sarah: Update user stories\n- [ ] Mike: Review technical specifications\n- [ ] Alex: Prepare design mockups",
  },
  {
    id: 5,
    parent_id: 4,
    title: "Sprint Retrospective",
    text: "# Sprint Retrospective\n\n## What went well?\n\n- Team collaboration improved\n- Delivered features on time\n- Good code review process\n\n## What could be improved?\n\n- Better estimation accuracy\n- More frequent stakeholder updates\n- Automated testing coverage",
  },
];

export function NoteApp() {
  const [selectedNoteId, setSelectedNoteId] = useState<number>(1);
  const [notes, setNotes] = useState<Note[]>(mockNotes);
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);

  const selectedNote = notes.find(note => note.id === selectedNoteId);

  const updateNote = (noteId: number, updates: Partial<Note>) => {
    setNotes(prev => prev.map(note => 
      note.id === noteId ? { ...note, ...updates } : note
    ));
  };

  const buildNoteTree = () => {
    interface NoteWithChildren extends Note {
      children: NoteWithChildren[];
    }
    
    const noteMap = new Map(notes.map(note => [note.id, { ...note, children: [] as NoteWithChildren[] }]));
    const rootNotes: NoteWithChildren[] = [];
    
    notes.forEach(note => {
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
          notes={buildNoteTree()}
          selectedNoteId={selectedNoteId}
          onSelectNote={setSelectedNoteId}
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
        {selectedNote && (
          <NoteEditor
            note={selectedNote}
            onUpdateNote={(updates) => updateNote(selectedNote.id, updates)}
          />
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