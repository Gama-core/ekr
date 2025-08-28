import React from 'react';
import { 
  Bold, 
  Italic, 
  Underline,
  List,
  ListOrdered,
  Link,
  Code,
  Quote,
  Heading1,
  Heading2,
  Heading3
} from 'lucide-react';

interface MarkdownToolbarProps {
  onFormat: (format: string) => void;
}

export function MarkdownToolbar({ onFormat }: MarkdownToolbarProps) {
  const formatButtons = [
    { icon: Bold, format: 'bold', label: 'Bold' },
    { icon: Italic, format: 'italic', label: 'Italic' },
    { icon: Underline, format: 'underline', label: 'Underline' },
    { icon: Code, format: 'code', label: 'Inline Code' },
    { icon: Link, format: 'link', label: 'Link' },
    { icon: Heading1, format: 'h1', label: 'Heading 1' },
    { icon: Heading2, format: 'h2', label: 'Heading 2' },
    { icon: Heading3, format: 'h3', label: 'Heading 3' },
    { icon: List, format: 'ul', label: 'Bullet List' },
    { icon: ListOrdered, format: 'ol', label: 'Numbered List' },
    { icon: Quote, format: 'quote', label: 'Quote' },
  ];

  return (
    <div className="flex items-center gap-1 p-2 border-b border-gray-200 bg-gray-50">
      {formatButtons.map(({ icon: Icon, format, label }, index) => (
        <React.Fragment key={format}>
          {(index === 4 || index === 6 || index === 9) && (
            <div className="w-px h-6 bg-gray-300 mx-2" />
          )}
          <button
            onClick={() => onFormat(format)}
            className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-200 rounded transition-colors"
            title={label}
          >
            <Icon size={16} />
          </button>
        </React.Fragment>
      ))}
    </div>
  );
}