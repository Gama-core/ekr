// src/App.tsx

import React, { useState } from 'react';
import { FileExplorer } from './components/FileExplorer';
import { NoteEditor } from './components/NoteEditor';
import { AIAssistant } from './components/AIAssistant';
import { useNotes } from './hooks/useNotes';
import { Note } from './types/Note';
import { Brain, AlertTriangle } from 'lucide-react'; // ADDED: AlertTriangle icon

function App() {
  const { 
    treeNotes, 
    loading,
    error, // ADDED: Get error state from hook
    createNote, 
    updateNote, 
    deleteNote 
  } = useNotes();
  
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isAIAssistantOpen, setIsAIAssistantOpen] = useState(false);

  const handleSelectNote = (note: Note) => {
    setSelectedNote(note);
  };

  const toggleAIAssistant = () => {
    setIsAIAssistantOpen(!isAIAssistantOpen);
  };

  // ADDED: When a note is deleted, deselect it to avoid showing a deleted note
  const handleDeleteNote = async (noteId: number) => {
    if (selectedNote?.id === noteId) {
      setSelectedNote(null);
    }
    deleteNote(noteId);
  }

  return (
    <div className="h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 flex-shrink-0">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
            <Brain size={20} className="text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-800">Knowledge Base</h1>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-sm text-gray-500">
            {treeNotes.length} notes
          </div>
          <button
            onClick={toggleAIAssistant}
            className={`
              px-4 py-2 rounded-md text-sm font-medium transition-colors
              ${isAIAssistantOpen 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }
            `}
          >
            AI Tools
          </button>
        </div>
      </header>

      {/* ADDED: Error Banner */}
      {error && (
        <div className="bg-red-100 border-b border-red-300 text-red-800 px-4 py-2 flex items-center">
          <AlertTriangle className="mr-2" size={18} />
          <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer */}
        <FileExplorer
          treeNotes={treeNotes}
          selectedNoteId={selectedNote?.id || null}
          onSelectNote={handleSelectNote}
          onCreateNote={createNote}
          onDeleteNote={handleDeleteNote} // CHANGED: Use the new handler
          loading={loading}
        />

        {/* Note Editor */}
        <div className={`flex-1 transition-all duration-300 ${
          isAIAssistantOpen ? 'mr-80' : ''
        }`}>
          <NoteEditor
            selectedNote={selectedNote}
            onUpdateNote={updateNote}
          />
        </div>

        {/* AI Assistant */}
        <AIAssistant
          isOpen={isAIAssistantOpen}
          onToggle={toggleAIAssistant}
        />
      </div>
    </div>
  );
}

export default App;