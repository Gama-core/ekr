import React, { useState, useEffect, useCallback } from 'react';
import { Save, FileText } from 'lucide-react';
import { Note, UpdateNoteRequest } from '../types/Note';
import { MarkdownToolbar } from './MarkdownToolbar';

interface NoteEditorProps {
  selectedNote: Note | null;
  onUpdateNote: (noteId: number, updates: UpdateNoteRequest) => Promise<Note | null>;
}

export function NoteEditor({ selectedNote, onUpdateNote }: NoteEditorProps) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isModified, setIsModified] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (selectedNote) {
      setTitle(selectedNote.title);
      setContent(selectedNote.text);
      setIsModified(false);
    }
  }, [selectedNote]);

  const handleSave = useCallback(async () => {
    if (!selectedNote || !isModified) return;
    
    setIsSaving(true);
    try {
      await onUpdateNote(selectedNote.id, { title, text: content });
      setIsModified(false);
    } catch (error) {
      console.error('Failed to save note:', error);
    } finally {
      setIsSaving(false);
    }
  }, [selectedNote, title, content, isModified, onUpdateNote]);

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    setIsModified(true);
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setIsModified(true);
  };

  const handleFormat = (format: string) => {
    const textarea = document.getElementById('note-content') as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = content.substring(start, end);
    
    let newContent = content;
    let newCursorPos = start;

    switch (format) {
      case 'bold':
        newContent = content.substring(0, start) + `**${selectedText}**` + content.substring(end);
        newCursorPos = start + (selectedText ? 2 : 2);
        break;
      case 'italic':
        newContent = content.substring(0, start) + `*${selectedText}*` + content.substring(end);
        newCursorPos = start + (selectedText ? 1 : 1);
        break;
      case 'code':
        newContent = content.substring(0, start) + `\`${selectedText}\`` + content.substring(end);
        newCursorPos = start + (selectedText ? 1 : 1);
        break;
      case 'h1':
        newContent = content.substring(0, start) + `# ${selectedText}` + content.substring(end);
        newCursorPos = start + 2;
        break;
      case 'h2':
        newContent = content.substring(0, start) + `## ${selectedText}` + content.substring(end);
        newCursorPos = start + 3;
        break;
      case 'h3':
        newContent = content.substring(0, start) + `### ${selectedText}` + content.substring(end);
        newCursorPos = start + 4;
        break;
      case 'ul':
        newContent = content.substring(0, start) + `- ${selectedText}` + content.substring(end);
        newCursorPos = start + 2;
        break;
      case 'ol':
        newContent = content.substring(0, start) + `1. ${selectedText}` + content.substring(end);
        newCursorPos = start + 3;
        break;
      case 'quote':
        newContent = content.substring(0, start) + `> ${selectedText}` + content.substring(end);
        newCursorPos = start + 2;
        break;
      case 'link':
        newContent = content.substring(0, start) + `[${selectedText}](url)` + content.substring(end);
        newCursorPos = start + selectedText.length + 3;
        break;
    }

    setContent(newContent);
    setIsModified(true);
    
    // Reset cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  if (!selectedNote) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <FileText size={48} className="mx-auto mb-4 text-gray-300" />
          <p className="text-lg mb-2">No note selected</p>
          <p className="text-sm">Select a note from the file explorer to start editing</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <input
            type="text"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            className="text-2xl font-bold text-gray-800 bg-transparent border-none outline-none flex-1 mr-4"
            placeholder="Note title..."
          />
          <button
            onClick={handleSave}
            disabled={!isModified || isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
        {isModified && (
          <p className="text-sm text-orange-600 mt-1">Unsaved changes</p>
        )}
      </div>

      {/* Toolbar */}
      <MarkdownToolbar onFormat={handleFormat} />

      {/* Editor */}
      <div className="flex-1 p-6">
        <textarea
          id="note-content"
          value={content}
          onChange={(e) => handleContentChange(e.target.value)}
          className="w-full h-full resize-none border-none outline-none text-gray-700 leading-relaxed font-mono text-sm"
          placeholder="Start writing your note in markdown..."
        />
      </div>
    </div>
  );
}