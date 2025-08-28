import { Note, TreeNote } from '../types/Note';

export function buildNoteTree(notes: Note[]): TreeNote[] {
  console.log('Building tree with notes:', notes.length);

  const noteMap = new Map<number, TreeNote>();
  const rootNotes: TreeNote[] = [];

  // First pass: Convert all notes to TreeNote format and add to map
  notes.forEach(note => {
    noteMap.set(note.id, {
      ...note,
      children: [],
      level: 0
    });
  });

  console.log('Note map size:', noteMap.size);

  // Second pass: Build the tree structure
  notes.forEach(note => {
    const treeNote = noteMap.get(note.id)!;

    if (note.parent_id === null || note.parent_id === undefined) {
      // This is a root note
      rootNotes.push(treeNote);
      console.log('Root note found:', note.title, 'ID:', note.id);
    } else {
      // This is a child note
      const parent = noteMap.get(note.parent_id);
      if (parent) {
        treeNote.level = parent.level + 1;
        parent.children.push(treeNote);
        console.log('Child note added:', note.title, 'to parent:', parent.title);
      } else {
        // Parent not found, treat as root note (orphaned note)
        console.warn(`Parent ${note.parent_id} not found for note ${note.id} (${note.title}), treating as root`);
        rootNotes.push(treeNote);
      }
    }
  });

  // Sort root notes and children recursively
  const sortNotes = (noteList: TreeNote[]) => {
    noteList.sort((a, b) => a.id - b.id); // Sort by ID, or you could sort by title
    noteList.forEach(note => {
      if (note.children.length > 0) {
        sortNotes(note.children);
      }
    });
  };

  sortNotes(rootNotes);

  console.log('Final root notes:', rootNotes.length);
  console.log('Root notes:', rootNotes.map(n => ({ id: n.id, title: n.title, children: n.children.length })));

  return rootNotes;
}

export function getAllNotesFlat(treeNotes: TreeNote[]): TreeNote[] {
  const result: TreeNote[] = [];

  function traverse(notes: TreeNote[]) {
    notes.forEach(note => {
      result.push(note);
      if (note.children.length > 0) {
        traverse(note.children);
      }
    });
  }

  traverse(treeNotes);
  return result;
}

// Helper function to debug the tree structure
export function debugTreeStructure(treeNotes: TreeNote[], indent = 0): void {
  const prefix = '  '.repeat(indent);
  treeNotes.forEach(note => {
    console.log(`${prefix}${note.id}: ${note.title} (level: ${note.level}, children: ${note.children.length})`);
    if (note.children.length > 0) {
      debugTreeStructure(note.children, indent + 1);
    }
  });
}