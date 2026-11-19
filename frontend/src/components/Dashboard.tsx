import React, { useState, useEffect } from 'react';
import { Internship, WSMatchAlertPayload } from '../types';
import { 
  Briefcase, 
  CheckCircle2, 
  Sparkles, 
  Clock, 
  RefreshCw, 
  ExternalLink, 
  ChevronRight,
  Wifi,
  WifiOff
} from 'lucide-react';

interface DashboardProps {
  isConnected: boolean;
  onOpenMatchModal: (match: WSMatchAlertPayload) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ isConnected, onOpenMatchModal }) => {
  const [internships, setInternships] = useState<Internship[]>([]);
  const [filter, setFilter] = useState<'MATCHED' | 'APPLIED' | 'ALL'>('MATCHED');
  const [isLoading, setIsLoading] = useState(false);
  const [isScraping, setIsScraping] = useState(false);

  const fetchInternships = async () => {
    setIsLoading(true);
    try {
      const url = filter === 'ALL' 
        ? 'http://localhost:8000/api/v1/internships' 
        : `http://localhost:8000/api/v1/internships?status=${filter}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setInternships(data);
      }
    } catch (err) {
      console.error('Failed to fetch listings:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInternships();
  }, [filter]);

  const handleTriggerScraper = async () => {
    setIsScraping(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/internships/trigger-scrape', {
        method: 'POST',
      });
      if (res.ok) {
        setTimeout(() => {
          fetchInternships();
          setIsScraping(false);
        }, 3000);
      }
    } catch (err) {
      setIsScraping(false);
    }
  };

  const matchedCount = internships.filter(i => i.status === 'MATCHED').length;
  const appliedCount = internships.filter(i => i.status === 'APPLIED').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">InternScout</h1>
              <p className="text-xs text-slate-400">Autonomous Internshala Discovery & Tailoring</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
              {isConnected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <Wifi className="w-3.5 h-3.5" /> Engine Connected
                  </span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="text-rose-400 font-medium flex items-center gap-1">
                    <WifiOff className="w-3.5 h-3.5" /> Reconnecting...
                  </span>
                </>
              )}
            </div>

            <button
              onClick={handleTriggerScraper}
              disabled={isScraping}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isScraping ? 'animate-spin' : ''}`} />
              {isScraping ? 'Scraping Internshala...' : 'Trigger Scrape Now'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        
        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Scraper Cadence</div>
            <div className="text-2xl font-bold mt-1 text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-400" /> Hourly + Daily
            </div>
            <div className="text-xs text-indigo-300 mt-2">Stealth Playwright + Cookie Vault</div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Eligible Matches</div>
            <div className="text-2xl font-bold mt-1 text-emerald-400 flex items-center gap-2">
              <Sparkles className="w-5 h-5" /> {matchedCount}
            </div>
            <div className="text-xs text-slate-400 mt-2">Fit score &ge; 75% threshold</div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Auto-Applied</div>
            <div className="text-2xl font-bold mt-1 text-indigo-400 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5" /> {appliedCount}
            </div>
            <div className="text-xs text-slate-400 mt-2">Screening Q&A submitted</div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Catalog Monitored</div>
            <div className="text-2xl font-bold mt-1 text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-slate-400" /> {internships.length}
            </div>
            <div className="text-xs text-slate-400 mt-2">Deduplicated against DB</div>
          </div>
        </div>

        {/* Listings Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-6 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Monitored Internships</h2>
              <p className="text-xs text-slate-400">Live stream of opportunities discovered on Internshala</p>
            </div>

            {/* Filter Pills */}
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-medium">
              {(['MATCHED', 'APPLIED', 'ALL'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg transition ${
                    filter === tab
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab === 'MATCHED' ? 'High Matches (≥75%)' : tab === 'APPLIED' ? 'Submitted' : 'All Listings'}
                </button>
              ))}
            </div>
          </div>

          {/* Table / Cards */}
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">Loading catalog records...</div>
          ) : internships.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              No internships found for current filter. Click "Trigger Scrape Now" to query Internshala.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60">
              {internships.map((job) => (
                <div
                  key={job.id}
                  className="p-5 hover:bg-slate-800/30 transition flex items-center justify-between gap-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                        job.match_score >= 85
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : job.match_score >= 70
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {job.match_score}% Match
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {job.status}
                      </span>
                      {job.is_remote && (
                        <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                          Work From Home
                        </span>
                      )}
                    </div>

                    <h3 className="text-base font-semibold text-white truncate flex items-center gap-2">
                      {job.title}
                      <a href={job.url} target="_blank" rel="noreferrer" className="text-slate-500 hover:text-slate-300">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </h3>

                    <div className="text-xs text-slate-400 flex flex-wrap items-center gap-3 mt-1.5">
                      <span className="text-slate-300 font-medium">{job.company_name}</span>
                      <span>•</span>
                      <span>{job.stipend_raw || 'Unpaid'}</span>
                      <span>•</span>
                      <span>{job.duration_months} Months</span>
                    </div>

                    {job.skills_required.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap mt-2.5">
                        {job.skills_required.slice(0, 5).map((skill) => (
                          <span key={skill} className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    {job.status === 'MATCHED' && (
                      <button
                        onClick={() => {
                          // Synthesize payload to open review modal
                          onOpenMatchModal({
                            internship: job,
                            resume_version_id: job.id, // linked resume ID
                            match_score: job.match_score,
                            summary_verdict: job.eligibility_verdict?.summary_verdict || 'High candidate alignment',
                            missing_skills: job.missing_skills,
                            tailored_headline: `Software Engineer specializing in ${job.skills_required.slice(0, 2).join(', ')}`,
                            tailored_summary: 'Targeted developer with strong matching profile.',
                            bullet_diffs: [
                              {
                                section: 'Projects',
                                original_bullet: 'Developed web application using standard libraries.',
                                suggested_bullet: `Engineered high-throughput service integrating ${job.skills_required[0] || 'Python'} and modern REST architecture.`,
                                change_type: 'REPLACE',
                                reason: 'Aligns directly with core requirements in JD'
                              }
                            ],
                            cover_letter: `I am thrilled to apply for the ${job.title} internship at ${job.company_name}. My background in software engineering and hands-on experience directly match the skills required for this role.`,
                            assessment_answers: {
                              "Why should you be hired for this role?": `I possess project-backed proficiency in ${job.skills_required.slice(0, 3).join(', ')} and can contribute immediately to your engineering deliverables.`,
                              "Are you available for full-time duration?": "Yes, I am fully available for the required duration."
                            }
                          });
                        }}
                        className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
                      >
                        Review & Apply
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  );
};
