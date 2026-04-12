import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Cpu,
  Database,
  Wrench,
  Brain,
  MessageSquare
} from 'lucide-react';

interface TraceEvent {
  event_type: 'reasoning' | 'tool_considered' | 'tool_call' | 'kg_access' | 'internal_monologue';
  content: string;
  timestamp: number;
  metadata: Record<string, any>;
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  reasoning: <Brain className="w-4 h-4" />,
  tool_considered: <Wrench className="w-4 h-4" />,
  tool_call: <Wrench className="w-4 h-4 text-blue-500" />,
  kg_access: <Database className="w-4 h-4 text-green-500" />,
  internal_monologue: <MessageSquare className="w-4 h-4 text-gray-400" />,
};

const EVENT_COLORS: Record<string, string> = {
  reasoning: 'bg-blue-50 text-blue-700 border-blue-200',
  tool_considered: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  tool_call: 'bg-blue-100 text-blue-800 border-blue-300',
  kg_access: 'bg-green-50 text-green-700 border-green-200',
  internal_monologue: 'bg-gray-50 text-gray-600 border-gray-200',
};

export const ReasoningTraceView: React.FC<{ requestId: string }> = ({ requestId }) => {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!requestId) return;

    const eventSource = new EventSource(\`/api/trace/\${requestId}`);

    eventSource.onmessage = (event) => {
      try {
        const newEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, newEvent]);
      } catch (e) {
        console.error('Error parsing trace event:', e);
      }
    };

    eventSource.onerror = () => {
      setError('Failed to connect to trace stream');
    };

    return () => {
      eventSource.close();
    };
  }, [requestId]);

  if (error) return <div className="p-4 text-red-500">{error}</div>;

  return (
    <div className="flex flex-col gap-4 p-4 bg-white rounded-lg border border-gray-200 max-w-3xl mx-auto w-full shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-gray-600" />
          Reasoning Trace
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `trace-${requestId}.json`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="text-xs px-2 py-1 text-gray-500 hover:text-gray-700 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
          >
            Export Log
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-gray-100 rounded-md transition-colors"
          >
            {isExpanded ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </button>
        </div>
      </div>


      {isExpanded && (
        <div className="flex flex-col gap-3">
          {events.length === 0 && (
            <div className="text-center py-8 text-gray-400 italic">
              Waiting for trace events...
            </div>
          )}
          {events.map((event, index) => (
            <div
              key={index}
              className="relative pl-8 py-2 border-l-2 border-gray-300 transition-all animate-in fade-in slide-in-from-left-2"
            >
              <div className="absolute -left-2 top-3 w-4 h-4 rounded-full bg-white border-2 border-gray-400" />

              <div className={\`p-3 rounded-lg border \${EVENT_COLORS[event.event_type]} shadow-sm\`}>
                <div className="flex items-center gap-2 mb-1 font-medium text-xs uppercase tracking-wider">
                  {EVENT_ICONS[event.event_type]}
                  {event.event_type.replace('_', ' ')}
                </div>
                <div className="text-sm leading-relaxed">
                  {event.content}
                </div>
                {Object.keys(event.metadata).length > 0 && (
                  <div className="mt-2 pt-2 border-t border-current border-opacity-20 text-xs font-mono opacity-80">
                    {JSON.stringify(event.metadata)}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
