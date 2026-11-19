import React, { useState } from 'react';
import { BulletDiff } from '../types';
import { Check, Edit2, RotateCcw, Sparkles } from 'lucide-react';

interface DiffViewerProps {
  diff: BulletDiff;
  index: number;
  onUpdate: (index: number, newSuggested: string) => void;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diff, index, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [currentText, setCurrentText] = useState(diff.suggested_bullet);

  const handleSave = () => {
    onUpdate(index, currentText);
    setIsEditing(false);
  };

  const handleReset = () => {
    setCurrentText(diff.suggested_bullet);
    onUpdate(index, diff.suggested_bullet);
    setIsEditing(false);
  };

  return (
    <div className="border border-slate-700/60 bg-slate-800/40 rounded-xl p-4 my-3 transition-all hover:border-slate-600">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          {diff.section}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 italic flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            {diff.reason}
          </span>
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition"
              title="Edit wording"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
          ) : (
            <div className="flex items-center gap-1">
              <button
                onClick={handleSave}
                className="p-1 rounded bg-emerald-600 text-white hover:bg-emerald-500 transition"
                title="Save changes"
              >
                <Check className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleReset}
                className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition"
                title="Reset to LLM suggestion"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Original Bullet */}
      <div className="mb-2 p-2 rounded-lg bg-rose-950/20 border border-rose-900/30 text-rose-300 text-sm">
        <div className="text-[11px] font-semibold text-rose-400/80 uppercase mb-1">Original Bullet:</div>
        <p className="line-through decoration-rose-500/60 opacity-90">{diff.original_bullet}</p>
      </div>

      {/* Suggested Bullet */}
      <div className="p-2 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-300 text-sm">
        <div className="text-[11px] font-semibold text-emerald-400 uppercase mb-1 flex items-center justify-between">
          <span>Tailored Recommendation:</span>
          {isEditing && <span className="text-xs text-amber-400 font-normal">Editing in progress...</span>}
        </div>
        {isEditing ? (
          <textarea
            value={currentText}
            onChange={(e) => setCurrentText(e.target.value)}
            className="w-full bg-slate-900/80 border border-emerald-500/50 rounded p-2 text-emerald-100 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-400"
            rows={3}
          />
        ) : (
          <p className="font-medium text-emerald-200">{currentText}</p>
        )}
      </div>
    </div>
  );
};
