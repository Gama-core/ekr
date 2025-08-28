import React, { useState, useMemo, useEffect, useCallback } from 'react';
import {
  FileText,
  Plus,
  ChevronRight,
  ChevronDown,
  Trash2,
  FolderOpen,
  Search
} from 'lucide-react';
import { TreeNote, Note, CreateNoteRequest } from '../types/Note';

interface FileExplorerProps {
  treeNotes: TreeNote[];
  selectedNoteId: number | null;
  onSelectNote: (note: Note) => void;
  onCreateNote: (noteData: CreateNoteRequest) => Promise<Note | null>;
  onDeleteNote: (noteId: number) => void;
  loading: boolean;
}

// Fixed recursive function to render the note tree
const NoteTreeItem = ({
  note,
  selectedNoteId,
  expandedNodes,
  toggleExpanded,
  onSelectNote,
  handleCreateSubNote,
  handleDeleteNote
}: {
  note: TreeNote;
  selectedNoteId: number | null;
  expandedNodes: Set<number>;
  toggleExpanded: (noteId: number) => void;
  onSelectNote: (note: Note) => void;
  handleCreateSubNote: (parentId: number) => void;
  handleDeleteNote: (noteId: number, e: React.MouseEvent) => void;
}) => {
  const isExpanded = expandedNodes.has(note.id);
  const isSelected = selectedNoteId === note.id;
  const hasChildren = note.children.length > 0;
  const paddingLeft = note.level * 20 + 12;

  return (
    <div key={note.id} className="select-none">
      <div
        className={`
          flex items-center py-2 px-3 cursor-pointer rounded-md mx-2 group
          ${isSelected 
            ? 'bg-blue-100 text-blue-900' 
            : 'hover:bg-gray-100 text-gray-700'
          }
        `}
        style={{ paddingLeft }}
        onClick={() => onSelectNote(note)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleExpanded(note.id);
            }}
            className="mr-1 p-0.5 hover:bg-gray-200 rounded"
          >
            {isExpanded ? (
              <ChevronDown size={14} className="text-gray-500" />
            ) : (
              <ChevronRight size={14} className="text-gray-500" />
            )}
          </button>
        ) : (
          <div className="w-5 mr-1" /> // Placeholder for alignment
        )}

        <FileText size={16} className={`mr-2 flex-shrink-0 ${
          isSelected ? 'text-blue-600' : 'text-gray-400'
        }`} />

        <span className="flex-1 text-sm font-medium truncate">
          {note.title}
        </span>

        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCreateSubNote(note.id);
            }}
            className="p-1 hover:bg-gray-200 rounded text-gray-500 hover:text-green-600"
            title="Add sub-note"
          >
            <Plus size={12} />
          </button>
          <button
            onClick={(e) => handleDeleteNote(note.id, e)}
            className="p-1 hover:bg-gray-200 rounded text-gray-500 hover:text-red-600"
            title="Delete note"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* FIXED: Recursive render - changed 'note.children' to 'child' */}
      {isExpanded && hasChildren && (
        <div>
          {note.children.map(child => (
            <NoteTreeItem
              key={child.id}
              note={child}
              selectedNoteId={selectedNoteId}
              expandedNodes={expandedNodes}
              toggleExpanded={toggleExpanded}
              onSelectNote={onSelectNote}
              handleCreateSubNote={handleCreateSubNote}
              handleDeleteNote={handleDeleteNote}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export function FileExplorer({
  treeNotes,
  selectedNoteId,
  onSelectNote,
  onCreateNote,
  onDeleteNote,
  loading
}: FileExplorerProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  // When notes are loaded, expand the first note by default
  useEffect(() => {
    if (treeNotes.length > 0) {
      setExpandedNodes(prev => new Set(prev.add(treeNotes[0].id)));
    }
  }, [treeNotes]);

  const toggleExpanded = (noteId: number) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(noteId)) {
        newSet.delete(noteId);
      } else {
        newSet.add(noteId);
      }
      return newSet;
    });
  };

  const handleCreateRootNote = async () => {
    await onCreateNote({
      title: 'New Note',
      text: '# New Note\n\nStart writing your thoughts here...'
    });
  };

  const handleCreateSubNote = async (parentId: number) => {
    await onCreateNote({
      title: 'New Sub Note',
      text: '# New Sub Note\n\nThis is a sub-note...',
      parent_id: parentId
    });
    // Ensure the parent is expanded to show the new sub-note
    setExpandedNodes(prev => new Set(prev.add(parentId)));
  };

  const handleDeleteNote = async (noteId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this note and all its children?')) {
      await onDeleteNote(noteId);
    }
  };

  // Smarter, recursive filter for the tree structure
  const filterTree = useCallback((nodes: TreeNote[], term: string): TreeNote[] => {
    if (!term) return nodes;
    const lowercasedTerm = term.toLowerCase();

    return nodes.reduce((acc, note) => {
      const children = filterTree(note.children, term);
      const selfMatches = note.title.toLowerCase().includes(lowercasedTerm);

      if (selfMatches || children.length > 0) {
        acc.push({ ...note, children });
      }
      return acc;
    }, [] as TreeNote[]);
  }, []);

  // Automatically expand nodes when searching
  useEffect(() => {
    if (searchTerm) {
      const newExpanded = new Set<number>();
      const addAllIds = (nodes: TreeNote[]) => {
        nodes.forEach(note => {
          newExpanded.add(note.id);
          addAllIds(note.children); // FIXED: changed from 'note.children' reference error
        });
      };
      addAllIds(filterTree(treeNotes, searchTerm));
      setExpandedNodes(newExpanded);
    }
  }, [searchTerm, treeNotes, filterTree]);

  const filteredTreeNotes = useMemo(() => filterTree(treeNotes, searchTerm), [treeNotes, searchTerm, filterTree]);

  if (loading) {
    return (
      <div className="w-80 bg-gray-50 border-r border-gray-200 flex items-center justify-center">
        <div className="text-gray-500 text-center">
          <FolderOpen size={32} className="mx-auto mb-2 text-gray-300" />
          <p>Loading notes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gray-50 border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center">
            <FolderOpen size={20} className="mr-2 text-blue-600" />
            Files
          </h2>
          <button
            onClick={handleCreateRootNote}
            className="p-2 hover:bg-gray-100 rounded-md text-gray-600 hover:text-blue-600"
            title="Create new note"
          >
            <Plus size={18} />
          </button>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {filteredTreeNotes.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <FileText size={32} className="mx-auto mb-2 text-gray-300" />
            <p className="text-sm">{searchTerm ? 'No notes found' : 'No notes yet'}</p>
            <button
              onClick={handleCreateRootNote}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700"
            >
              Create your first note
            </button>
          </div>
        ) : (
          // Render the tree recursively
          filteredTreeNotes.map(note => (
            <NoteTreeItem
              key={note.id}
              note={note}
              selectedNoteId={selectedNoteId}
              expandedNodes={expandedNodes}
              toggleExpanded={toggleExpanded}
              onSelectNote={onSelectNote}
              handleCreateSubNote={handleCreateSubNote}
              handleDeleteNote={handleDeleteNote}
            />
          ))
        )}
      </div>
    </div>
  );
}