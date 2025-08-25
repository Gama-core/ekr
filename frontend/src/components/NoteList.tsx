// src/components/NoteList.tsx
import React from 'react';
import { Note } from '../types/note';

interface NoteListProps {
  notes: Note[];
  onSelectNote: (note: Note) => void;
  onDeleteNote: (id: number) => void;
  isLoading: boolean;
}

const NoteList: React.FC<NoteListProps> = ({ notes, onSelectNote, onDeleteNote, isLoading }) => {
  return (
    <div className="note-list">
      <h2>Notes</h2>
      {isLoading ? (
        <p>Loading...</p>
      ) : notes.length === 0 ? (
        <p>No notes found. Create one!</p>
      ) : (
        <ul>
          {notes.map((note) => (
            <li key={note.id}>
              <span>{note.title}</span>
              <div className="note-actions">
                <button onClick={() => onSelectNote(note)}>Edit</button>
                <button className="delete" onClick={() => onDeleteNote(note.id)}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default NoteList;