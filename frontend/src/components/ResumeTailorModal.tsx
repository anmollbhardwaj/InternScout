import React, { useState } from 'react';
import { WSMatchAlertPayload, BulletDiff } from '../types';
import { DiffViewer } from './DiffViewer';
import { 
  X, 
  Send, 
  XCircle, 
  ExternalLink, 
  Building2, 
  MapPin, 
  Banknote, 
  Calendar, 
  AlertTriangle,
  Sparkles,
  Loader2,
  FileText
} from 'lucide-react';

interface ResumeTailorModalProps {
  data: WSMatchAlertPayload;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (payload: {
    resume_version_id: string;
    modified_bullet_diffs: BulletDiff[];
    modified_cover_letter: string;
    modified_assessment_answers: Record<string, string>;
  }) => Promise<void>;
  onSkip: (internshipId: string) => Promise<void>;
}

export const ResumeTailorModal: React.FC<ResumeTailorModalProps> = ({
  data,
  isOpen,
  onClose,
  onApprove,
  onSkip,
}) => {
  const { internship } = data;
  const [activeTab, setActiveTab] = useState<'diffs' | 'cover_letter' | 'qa'>('diffs');
  const [diffs, setDiffs] = useState<BulletDiff[]>(data.bullet_diffs);
  const [coverLetter, setCoverLetter] = useState<string>(data.cover_letter);
  const [assessmentAnswers, setAssessmentAnswers] = useState<Record<string, string>>(data.assessment_answers);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionProgress, setSubmissionProgress] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleBulletUpdate = (index: number, newSuggested: string) => {
    setDiffs((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], suggested_bullet: newSuggested };
      return updated;
    });
  };

  const handleApproveClick = async () => {
    try {
      setIsSubmitting(true);
      setSubmissionProgress('Queuing application and launching stealth browser...');
      await onApprove({
        resume_version_id: data.resume_version_id,
        modified_bullet_diffs: diffs,
        modified_cover_letter: coverLetter,
        modified_assessment_answers: assessmentAnswers,
      });
      setSubmissionProgress('Application queued successfully! Executing in background.');
      setTimeout(() => {
        setIsSubmitting(false);
        onClose();
      }, 1800);
    } catch (err) {
      setIsSubmitting(false);
      setSubmissionProgress('Error approving application.');
    }
  };

  const handleSkipClick = async () => {
    await onSkip(internship.id);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden text-slate-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-6 border-b border-slate-800 bg-slate-900/90 flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <span className="px-3 py-1 text-sm font-bold rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                {data.match_score}% Match Score
              </span>
              <span className="text-xs uppercase font-medium text-slate-400 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                {internship.is_remote ? 'Remote / Work From Home' : internship.locations.join(', ')}
              </span>
            </div>

            <h2 className="text-2xl font-bold mt-2 text-white flex items-center gap-2">
              {internship.title}
              <a 
                href={internship.url} 
                target="_blank" 
                rel="noreferrer"
                className="text-slate-400 hover:text-indigo-400 transition"
                title="Open Internshala Listing"
              >
                <ExternalLink className="w-5 h-5" />
              </a>
            </h2>

            <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-slate-300">
              <span className="flex items-center gap-1.5 text-indigo-300">
                <Building2 className="w-4 h-4" /> {internship.company_name}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <Banknote className="w-4 h-4 text-emerald-400" /> {internship.stipend_raw || 'Unpaid'}
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <Calendar className="w-4 h-4 text-amber-400" /> {internship.duration_months} Months
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Missing Keywords & Verdict Summary */}
        <div className="px-6 py-3 bg-slate-950/40 border-b border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <span className="font-semibold text-slate-400">AI Verdict:</span>
            <span>{data.summary_verdict}</span>
          </div>
          {data.missing_skills.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-amber-400 flex items-center gap-1 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" /> Missing Keywords:
              </span>
              {data.missing_skills.map((skill) => (
                <span key={skill} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-900/60 px-6 pt-2">
          <button
            onClick={() => setActiveTab('diffs')}
            className={`pb-3 px-4 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              activeTab === 'diffs'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Resume Diff Suggestions ({diffs.length})
          </button>
          <button
            onClick={() => setActiveTab('cover_letter')}
            className={`pb-3 px-4 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              activeTab === 'cover_letter'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            Why Should You Be Hired?
          </button>
          <button
            onClick={() => setActiveTab('qa')}
            className={`pb-3 px-4 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              activeTab === 'qa'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Assessment Q&A ({Object.keys(assessmentAnswers).length})
          </button>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {activeTab === 'diffs' && (
            <div>
              <p className="text-sm text-slate-400 mb-3">
                Review specific bullet tweaks generated to align your real experience with this internship's requirements. Click the edit icon to adjust wording before applying.
              </p>
              {diffs.length === 0 ? (
                <div className="p-8 text-center text-slate-500 border border-dashed border-slate-800 rounded-xl">
                  Your base resume already strongly matches all JD key phrases. No mandatory bullet adjustments needed!
                </div>
              ) : (
                diffs.map((diff, idx) => (
                  <DiffViewer
                    key={idx}
                    diff={diff}
                    index={idx}
                    onUpdate={handleBulletUpdate}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === 'cover_letter' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-slate-200">
                  "Why should you be hired for this role?" Response:
                </label>
                <span className="text-xs text-slate-400">
                  {coverLetter.trim().split(/\s+/).filter(Boolean).length} words
                </span>
              </div>
              <textarea
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                rows={10}
                className="w-full bg-slate-950 border border-slate-700/80 rounded-xl p-4 text-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                placeholder="Grounded cover letter response..."
              />
              <p className="text-xs text-slate-500 mt-2">
                Grounded strictly in your profile facts; connects your base projects with {internship.company_name}'s requirements.
              </p>
            </div>
          )}

          {activeTab === 'qa' && (
            <div className="space-y-4">
              <p className="text-sm text-slate-400">
                Pre-generated answers for common Internshala screening questions:
              </p>
              {Object.entries(assessmentAnswers).map(([question, answer], idx) => (
                <div key={idx} className="p-4 bg-slate-950 rounded-xl border border-slate-800">
                  <div className="text-xs font-semibold uppercase text-indigo-400 mb-1">
                    Question {idx + 1}:
                  </div>
                  <div className="text-sm font-medium text-slate-200 mb-2">{question}</div>
                  <textarea
                    value={answer}
                    onChange={(e) => {
                      const newAns = { ...assessmentAnswers, [question]: e.target.value };
                      setAssessmentAnswers(newAns);
                    }}
                    rows={3}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handleSkipClick}
              disabled={isSubmitting}
              className="px-4 py-2.5 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-300 text-sm font-medium transition flex items-center gap-2 disabled:opacity-50"
            >
              <XCircle className="w-4 h-4 text-rose-400" />
              Skip Internship
            </button>
          </div>

          <div className="flex items-center gap-3">
            {submissionProgress && (
              <span className="text-xs text-indigo-400 font-medium flex items-center gap-1.5 animate-pulse">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {submissionProgress}
              </span>
            )}
            <button
              onClick={handleApproveClick}
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white font-semibold text-sm transition shadow-lg shadow-indigo-500/20 flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Applying via Playwright...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Approve & Auto-Apply
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
