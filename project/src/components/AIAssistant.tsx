import React, { useState } from 'react';
import { 
  Bot, 
  Send, 
  X, 
  ChevronLeft,
  FileText,
  Lightbulb,
  BarChart3,
  Quote,
  Bookmark,
  Sparkles
} from 'lucide-react';

interface AIAssistantProps {
  isOpen: boolean;
  onToggle: () => void;
}

const aiTools = [
  {
    id: 'custom-block',
    name: 'Custom AI Block',
    description: 'Create a custom AI-powered block',
    icon: Sparkles,
    color: 'text-purple-600'
  },
  {
    id: 'summary',
    name: 'AI Summary',
    description: 'Generate a summary of the document',
    icon: FileText,
    color: 'text-blue-600'
  },
  {
    id: 'key-points',
    name: 'Key Points',
    description: 'Extract key points from the document',
    icon: BarChart3,
    color: 'text-green-600'
  },
  {
    id: 'insights',
    name: 'AI Insights',
    description: 'Generate insights and analysis',
    icon: Lightbulb,
    color: 'text-orange-600'
  },
  {
    id: 'citations',
    name: 'Citations',
    description: 'Generate citations and sources',
    icon: Quote,
    color: 'text-indigo-600'
  }
];

export function AIAssistant({ isOpen, onToggle }: AIAssistantProps) {
  const [message, setMessage] = useState('');
  const [showTools, setShowTools] = useState(false);

  const handleSendMessage = () => {
    if (message.trim()) {
      // TODO: Implement AI chat functionality
      console.log('Sending message:', message);
      setMessage('');
    }
  };

  const handleToolClick = (toolId: string) => {
    // TODO: Implement tool functionality
    console.log('Tool clicked:', toolId);
    setShowTools(false);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-4 top-1/2 transform -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-l-lg shadow-lg transition-colors z-10"
        title="Open AI Assistant"
      >
        <Bot size={20} />
      </button>
    );
  }

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Bot size={20} className="mr-2 text-blue-600" />
            <h3 className="font-semibold text-gray-800">AI Assistant</h3>
          </div>
          <button
            onClick={onToggle}
            className="p-1 hover:bg-gray-200 rounded-md text-gray-500"
          >
            <X size={18} />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">Coming soon - AI-powered assistance</p>
      </div>

      {/* AI Tools */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={() => setShowTools(!showTools)}
          className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <div className="flex items-center">
            <Sparkles size={16} className="mr-2 text-blue-600" />
            <span className="text-sm font-medium text-gray-700">AI Blocks</span>
          </div>
          <ChevronLeft 
            size={16} 
            className={`text-gray-400 transition-transform ${showTools ? 'rotate-90' : '-rotate-90'}`} 
          />
        </button>

        {showTools && (
          <div className="mt-2 space-y-1">
            {aiTools.map((tool) => {
              const Icon = tool.icon;
              return (
                <button
                  key={tool.id}
                  onClick={() => handleToolClick(tool.id)}
                  className="w-full flex items-start p-3 hover:bg-gray-50 rounded-lg text-left transition-colors group"
                  disabled
                >
                  <Icon size={16} className={`mr-3 mt-0.5 ${tool.color} group-disabled:text-gray-400`} />
                  <div className="flex-1">
                    <h4 className="text-sm font-medium text-gray-700 group-disabled:text-gray-400">
                      {tool.name}
                    </h4>
                    <p className="text-xs text-gray-500 group-disabled:text-gray-400">
                      {tool.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="text-center text-gray-500 mt-8">
          <Bot size={48} className="mx-auto mb-4 text-gray-300" />
          <h4 className="text-lg font-medium text-gray-700 mb-2">AI Assistant</h4>
          <p className="text-sm text-gray-500 mb-4">
            Your intelligent writing companion will be available soon.
          </p>
          <div className="text-xs text-gray-400 space-y-1">
            <p>• Document analysis and insights</p>
            <p>• Writing assistance and suggestions</p>
            <p>• Content summarization</p>
            <p>• Research and fact-checking</p>
          </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200">
        <div className="relative">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask AI anything, use @ to mention documents..."
            className="w-full pr-12 pl-4 py-3 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-gray-50"
            disabled
          />
          <button
            onClick={handleSendMessage}
            disabled={!message.trim()}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 text-gray-400 hover:text-blue-600 disabled:cursor-not-allowed"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          AI features coming soon
        </p>
      </div>
    </div>
  );
}