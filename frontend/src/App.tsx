// src/App.tsx
import React, { useState, useEffect } from 'react';
import type { Note } from './types/note';
import * as api from './services/api';
import NoteList from './components/NoteList';
import NoteForm from './components/NoteForm';

function App() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNotes();
  }, []);

  const fetchNotes = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const fetchedNotes = await api.getAllNotes();
      setNotes(fetchedNotes);
    } catch (err) {
      setError('Failed to fetch notes. Is the API gateway service running on port 8000?');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectNote = (note: Note) => {
    setSelectedNote(note);
  };

  const handleCancel = () => {
    setSelectedNote(null);
  };

  const handleSubmit = async (noteData: api.NoteCreatePayload) => {
    try {
      if (selectedNote) {
        // Update existing note
        const updatedNote = await api.updateNote(selectedNote.id, noteData);
        setNotes(notes.map((n) => (n.id === updatedNote.id ? updatedNote : n)));
      } else {
        // Create new note
        const newNote = await api.createNote(noteData);
        setNotes([...notes, newNote]);
      }
      setSelectedNote(null);
    } catch (err) {
      setError('Failed to save the note.');
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this note?')) {
        try {
            await api.deleteNote(id);
            setNotes(notes.filter((n) => n.id !== id));
        } catch (err) {
            setError('Failed to delete the note.');
            console.error(err);
        }
    }
  };

  return (
    <div className="app-container">
      <header>
        <h1>Extended Knowledge Repository</h1>
        <button onClick={fetchNotes} disabled={isLoading}>Refresh Notes</button>
      </header>
      <main className="main-content">
        <NoteList
          notes={notes}
          onSelectNote={handleSelectNote}
          onDeleteNote={handleDelete}
          isLoading={isLoading}
        />
        <NoteForm
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          initialData={selectedNote}
        />
      </main>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default App;