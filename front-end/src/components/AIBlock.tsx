import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles, Copy, Check, X, RefreshCw } from "lucide-react";
import { useState } from "react";

interface AIBlockProps {
  type: 'summary' | 'fact-check' | 'update';
  content: any;
  onApplyCorrections?: () => void;
  onSaveUpdate?: () => void;
  onDiscard: () => void;
}

export function AIBlock({ type, content, onApplyCorrections, onSaveUpdate, onDiscard }: AIBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderSummary = () => (
    <Card className="border-ai-border bg-ai-secondary">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-ai-primary">
          <Sparkles className="h-5 w-5" />
          AI Summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-relaxed">{content.summary_text}</p>
        <div className="flex justify-between items-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCopy(content.summary_text)}
            className="gap-2"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDiscard}
            className="gap-2 text-subtle-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderFactCheck = () => (
    <Card className="border-ai-border bg-ai-secondary">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-ai-primary">
          <Sparkles className="h-5 w-5" />
          Fact-Check Suggestions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          {content.corrections.map((correction: any, index: number) => (
            <div key={index} className="p-3 bg-background rounded-md border border-panel-border">
              <div className="space-y-2">
                <div>
                  <span className="text-xs font-medium text-destructive">Inaccurate Quote:</span>
                  <p className="text-sm mt-1 text-muted-foreground">{correction.inaccurate_quote}</p>
                </div>
                <div>
                  <span className="text-xs font-medium text-success">Suggested Correction:</span>
                  <p className="text-sm mt-1">{correction.suggested_correction}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="flex justify-between items-center pt-2">
          <Button
            onClick={onApplyCorrections}
            className="gap-2 bg-ai-primary hover:bg-ai-primary/90"
          >
            <Check className="h-4 w-4" />
            Apply these fixes
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDiscard}
            className="gap-2 text-subtle-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderUpdate = () => (
    <Card className="border-ai-border bg-ai-secondary">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-ai-primary">
          <Sparkles className="h-5 w-5" />
          AI Content Update
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="max-h-96 overflow-y-auto">
          <div className="p-4 bg-background rounded-md border border-panel-border">
            <pre className="whitespace-pre-wrap text-sm leading-relaxed font-mono">
              {content.updated_text}
            </pre>
          </div>
        </div>
        {content.changes && (
          <div className="p-3 bg-background rounded-md border border-panel-border">
            <span className="text-xs font-medium text-ai-primary">Changes Made:</span>
            <ul className="text-sm mt-1 space-y-1">
              {content.changes.map((change: string, index: number) => (
                <li key={index} className="flex items-start gap-2">
                  <Check className="h-3 w-3 text-success mt-0.5 flex-shrink-0" />
                  {change}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex justify-between items-center pt-2">
          <Button
            onClick={onSaveUpdate}
            className="gap-2 bg-ai-primary hover:bg-ai-primary/90"
          >
            <RefreshCw className="h-4 w-4" />
            Save Changes (Override)
          </Button>
          <Button
            variant="outline"
            onClick={onDiscard}
            className="gap-2"
          >
            <X className="h-4 w-4" />
            Discard
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  switch (type) {
    case 'summary':
      return renderSummary();
    case 'fact-check':
      return renderFactCheck();
    case 'update':
      return renderUpdate();
    default:
      return null;
  }
}