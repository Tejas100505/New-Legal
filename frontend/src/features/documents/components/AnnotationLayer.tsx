import { useState } from 'react';
import { useDocumentViewerStore } from '../store/documentViewerStore';
import { Badge } from '@/components/atoms/Badge';
import { Trash2, Plus, MessageSquare, X } from 'lucide-react';
import type { AnnotationType, AnnotationColor } from '@/types';

export function AnnotationLayer() {
  const annotations = useDocumentViewerStore((s) => s.annotations);
  const addAnnotation = useDocumentViewerStore((s) => s.addAnnotation);
  const deleteAnnotation = useDocumentViewerStore((s) => s.deleteAnnotation);

  const [isOpenForm, setIsOpenForm] = useState(false);
  const [text, setText] = useState('');
  const [note, setNote] = useState('');
  const [type, setType] = useState<AnnotationType>('highlight');
  const [color, setColor] = useState<AnnotationColor>('yellow');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text) return;
    
    addAnnotation({
      pageNumber: 1,
      type,
      color,
      text,
      note: note || undefined,
      startOffset: 0,
      endOffset: text.length,
    });

    setText('');
    setNote('');
    setIsOpenForm(false);
  };

  return (
    <div className="flex flex-col gap-4 text-left">
      <div className="flex justify-between items-center">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Active Annotations ({annotations.length})
        </span>
        <button
          onClick={() => setIsOpenForm(true)}
          className="flex items-center gap-1 text-[10px] bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/20 px-2 py-1 rounded-md transition-all"
        >
          <Plus className="h-3.5 w-3.5" /> Add New
        </button>
      </div>

      {/* New Annotation Form */}
      {isOpenForm && (
        <form onSubmit={handleAdd} className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg flex flex-col gap-3 relative">
          <button 
            type="button" 
            onClick={() => setIsOpenForm(false)} 
            className="absolute top-2 right-2 text-slate-500 hover:text-slate-300"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <h4 className="text-xs font-bold text-slate-200">New Annotation / Note</h4>
          
          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-500 uppercase font-semibold">Highlighted Text</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste selected text here..."
              rows={2}
              required
              className="w-full bg-slate-950 border border-slate-850 rounded p-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[10px] text-slate-500 uppercase font-semibold">Note / Comment</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add annotation description..."
              className="w-full bg-slate-950 border border-slate-850 rounded p-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-500 uppercase font-semibold">Annotation Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as AnnotationType)}
                className="bg-slate-950 border border-slate-850 rounded p-1 text-xs text-slate-200"
              >
                <option value="highlight">Highlight</option>
                <option value="note">Note Comment</option>
                <option value="flag">Risk Flag</option>
                <option value="redaction">Redaction</option>
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-slate-500 uppercase font-semibold">Highlight Color</label>
              <select
                value={color}
                onChange={(e) => setColor(e.target.value as AnnotationColor)}
                className="bg-slate-950 border border-slate-850 rounded p-1 text-xs text-slate-200"
              >
                <option value="yellow">Yellow</option>
                <option value="blue">Blue</option>
                <option value="green">Green</option>
                <option value="red">Red</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="w-full py-1.5 bg-indigo-500 hover:bg-indigo-600 rounded text-xs font-semibold text-white transition-all mt-1"
          >
            Create Annotation
          </button>
        </form>
      )}

      {/* List of Annotations */}
      <div className="flex flex-col gap-2 max-h-[350px] overflow-y-auto pr-1">
        {annotations.map((ann) => (
          <div key={ann.id} className="p-3 bg-slate-950/40 border border-slate-850 rounded-lg flex flex-col gap-2 relative group">
            <button
              onClick={() => deleteAnnotation(ann.id)}
              className="absolute top-2 right-2 text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
              title="Delete annotation"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>

            <div className="flex items-center gap-2">
              <Badge variant={ann.type === 'redaction' ? 'danger' : ann.type === 'flag' ? 'warning' : 'info'} size="xs" className="capitalize">
                {ann.type}
              </Badge>
              <span className="text-[9px] text-slate-500">Page {ann.pageNumber} · {new Date(ann.createdAt).toLocaleDateString()}</span>
            </div>

            <p className="text-xs text-slate-300 italic bg-slate-950/60 p-2 rounded border border-slate-850">
              "{ann.text}"
            </p>

            {ann.note && (
              <div className="flex items-start gap-1.5 text-[11px] text-slate-400">
                <MessageSquare className="h-3.5 w-3.5 text-indigo-400 shrink-0 mt-0.5" />
                <p>
                  <strong className="text-slate-300 font-semibold">{ann.createdBy}:</strong> {ann.note}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
