// src/hooks/useNotes.ts

import { useState, useEffect, useCallback } from 'react';
import { Note, TreeNote, CreateNoteRequest, UpdateNoteRequest } from '../types/Note';
import { buildNoteTree, debugTreeStructure } from '../utils/noteTree';

// The URL for your backend API Gateway
const API_BASE_URL = 'http://localhost:8000';

export function useNotes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [treeNotes, setTreeNotes] = useState<TreeNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load all notes from the API
  const loadNotes = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/notes`);
      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      const data: Note[] = await response.json();

      console.log('Loaded notes from API:', data.length);
      console.log('Notes data:', data);

      // Sort notes to ensure consistent ordering
      const sortedNotes = data.sort((a, b) => a.id - b.id);

      setNotes(sortedNotes);

      const tree = buildNoteTree(sortedNotes);
      console.log('Built tree with root notes:', tree.length);

      // Debug the tree structure
      console.log('=== TREE STRUCTURE ===');
      debugTreeStructure(tree);
      console.log('=== END TREE STRUCTURE ===');

      setTreeNotes(tree);
      setError(null);
    } catch (err) {
      setError('Failed to load notes. Make sure the backend service is running.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Create a new note via the API
  const createNote = useCallback(async (noteData: CreateNoteRequest): Promise<Note | null> => {
    try {
      console.log('Creating note:', noteData);
      const response = await fetch(`${API_BASE_URL}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(noteData),
      });
      if (!response.ok) throw new Error('Failed to create note.');

      const newNote: Note = await response.json();
      console.log('Created note:', newNote);

      const updatedNotes = [...notes, newNote].sort((a, b) => a.id - b.id);
      setNotes(updatedNotes);

      const tree = buildNoteTree(updatedNotes);
      setTreeNotes(tree);

      return newNote;
    } catch (err) {
      setError('Failed to create note.');
      console.error(err);
      return null;
    }
  }, [notes]);

  // Update a note via the API
  const updateNote = useCallback(async (noteId: number, updates: UpdateNoteRequest): Promise<Note | null> => {
    try {
      console.log('Updating note:', noteId, updates);
      const response = await fetch(`${API_BASE_URL}/notes/${noteId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (!response.ok) throw new Error('Failed to update note.');

      const updatedNote: Note = await response.json();
      console.log('Updated note:', updatedNote);

      const updatedNotes = notes.map(note =>
        note.id === noteId ? updatedNote : note
      ).sort((a, b) => a.id - b.id);

      setNotes(updatedNotes);

      const tree = buildNoteTree(updatedNotes);
      setTreeNotes(tree);

      return updatedNote;
    } catch (err) {
      setError('Failed to update note.');
      console.error(err);
      return null;
    }
  }, [notes]);

  // Delete a note via the API
  const deleteNote = useCallback(async (noteId: number): Promise<boolean> => {
    try {
      console.log('Deleting note:', noteId);
      const response = await fetch(`${API_BASE_URL}/notes/${noteId}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete note.');

      // Client-side logic to remove the note and its children from the state
      // This provides a fast UI update without needing to refetch all notes
      function removeNoteAndChildren(notesList: Note[], targetId: number): Note[] {
        const childrenIds = notesList
          .filter(n => n.parent_id === targetId)
          .map(n => n.id);

        let filteredNotes = notesList.filter(n => n.id !== targetId);

        childrenIds.forEach(childId => {
          filteredNotes = removeNoteAndChildren(filteredNotes, childId);
        });

        return filteredNotes;
      }

      const updatedNotes = removeNoteAndChildren(notes, noteId).sort((a, b) => a.id - b.id);
      setNotes(updatedNotes);

      const tree = buildNoteTree(updatedNotes);
      setTreeNotes(tree);

      console.log('Deleted note and updated tree');
      return true;
    } catch (err) {
      setError('Failed to delete note.');
      console.error(err);
      return false;
    }
  }, [notes]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  return {
    notes,
    treeNotes,
    loading,
    error,
    loadNotes,
    createNote,
    updateNote,
    deleteNote
  };
}