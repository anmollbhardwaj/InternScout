import React, { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { ResumeTailorModal } from './components/ResumeTailorModal';
import { useWebSocket } from './hooks/useWebSocket';
import { WSMatchAlertPayload, BulletDiff } from './types';

export const App: React.FC = () => {
  const [activeModalData, setActiveModalData] = useState<WSMatchAlertPayload | null>(null);

  // Request browser desktop notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Real-Time WebSocket hook
  const { isConnected } = useWebSocket({
    url: 'ws://localhost:8000/ws',
    onMatchAlert: (payload: WSMatchAlertPayload) => {
      console.log('Incoming real-time match alert:', payload);
      setActiveModalData(payload);

      // Desktop system push notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(`New Match Found: ${payload.internship.title}`, {
          body: `${payload.match_score}% match at ${payload.internship.company_name}. Click to review tailored resume!`,
          icon: '/favicon.ico',
        });
      }
    },
    onProgress: (progress) => {
      console.log('Application progress:', progress);
    },
  });

  const handleApproveApplication = async (payload: {
    resume_version_id: string;
    modified_bullet_diffs: BulletDiff[];
    modified_cover_letter: string;
    modified_assessment_answers: Record<string, string>;
  }) => {
    const res = await fetch('http://localhost:8000/api/v1/applications/approve-and-apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        resume_version_id: payload.resume_version_id,
        modified_bullet_diffs: payload.modified_bullet_diffs,
        modified_cover_letter: payload.modified_cover_letter,
        modified_assessment_answers: payload.modified_assessment_answers,
        auto_apply_now: true,
      }),
    });
    if (!res.ok) {
      throw new Error('Failed to submit application');
    }
  };

  const handleSkipApplication = async (internshipId: string) => {
    await fetch(`http://localhost:8000/api/v1/applications/skip/${internshipId}`, {
      method: 'POST',
    });
  };

  return (
    <>
      <Dashboard
        isConnected={isConnected}
        onOpenMatchModal={(match) => setActiveModalData(match)}
      />

      {activeModalData && (
        <ResumeTailorModal
          data={activeModalData}
          isOpen={!!activeModalData}
          onClose={() => setActiveModalData(null)}
          onApprove={handleApproveApplication}
          onSkip={handleSkipApplication}
        />
      )}
    </>
  );
};

export default App;
