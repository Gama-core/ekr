// src/types/note.ts
export default interface Note {
  id: number;
  owner_id: number;
  title: string;
  text: string | null;
  parent_id: number | null;
  color: string | null;
  creation_date: string | null; // Keep as string for simplicity
  version: number;
}

// Also export as named export for compatibility
export { Note };