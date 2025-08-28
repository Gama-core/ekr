// src/types/Note.ts

export interface Note {
  id: number;
  owner_id: number;
  title: string;
  text: string | null; // CHANGED: Text can be null from the backend
  parent_id: number | null;
  color: string | null;
  creation_date: string | null; // CHANGED: This can also be null
  version: number;
}

export interface TreeNote extends Note {
  children: TreeNote[];
  level: number;
}

// For creating a new note
export interface CreateNoteRequest {
  title: string;
  text?: string; // CHANGED: Text is optional on creation
  parent_id?: number | null;
}

// For updating an existing note
export interface UpdateNoteRequest {
  title?: string;
  text?: string;
}