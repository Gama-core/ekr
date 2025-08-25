// src/services/api.ts
import axios from 'axios';
import type { Note } from '../types/note';

// Create an Axios instance with the base URL of our gateway
const apiClient = axios.create({
  baseURL: '/',
});

// Type for the note creation payload (without id, owner_id, etc.)
export type NoteCreatePayload = Omit<Note, 'id' | 'owner_id' | 'creation_date' | 'version'>;
export type NoteUpdatePayload = Partial<NoteCreatePayload>;

export const getAllNotes = async (): Promise<Note[]> => {
  const response = await apiClient.get('/notes');
  return response.data;
};

export const getNoteById = async (id: number): Promise<Note> => {
    const response = await apiClient.get(`/notes/${id}`);
    return response.data;
}

export const createNote = async (note: NoteCreatePayload): Promise<Note> => {
  const response = await apiClient.post('/notes', note);
  return response.data;
};

export const updateNote = async (id: number, note: NoteUpdatePayload): Promise<Note> => {
  const response = await apiClient.put(`/notes/${id}`, note);
  return response.data;
};

export const deleteNote = async (id: number): Promise<void> => {
  await apiClient.delete(`/notes/${id}`);
};