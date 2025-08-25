// src/components/NoteForm.tsx
import React, { useState, useEffect } from 'react';
import { Note } from '../types/note';
import { NoteCreatePayload } from '../services/api';

interface NoteFormProps {
  onSubmit: (note: NoteCreatePayload) => void;
  onCancel: () => void;
  initialData: Note | null;
}

const NoteForm: React.FC<NoteFormProps> = ({ onSubmit, onCancel, initialData }) => {
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');

  useEffect(() => {
    if (initialData) {
      setTitle(initialData.title);
      setText(initialData.text || '');
    } else {
      // When we clear the selection, clear the form
      setTitle('');
      setText('');
    }
  }, [initialData]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
        alert('Title is required');
        return;
    }
    // We don't need parent_id or color for this basic form
    onSubmit({ title, text, parent_id: null, color: null });
  };

  return (
    <div className="note-form">
      <h2>{initialData ? 'Edit Note' : 'Create New Note'}</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Note Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          placeholder="Note content..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="form-actions">
          <button type="submit">Save</button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default NoteForm;