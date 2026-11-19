export interface Internship {
  id: string;
  internshala_id: string;
  title: string;
  company_name: string;
  locations: string[];
  is_remote: boolean;
  stipend_raw?: string;
  stipend_min_inr: number;
  stipend_max_inr: number;
  duration_months: number;
  apply_by?: string;
  url: string;
  about_internship?: string;
  skills_required: string[];
  who_can_apply?: string;
  perks: string[];
  number_of_openings: number;
  status: 'DISCOVERED' | 'EVALUATING' | 'MATCHED' | 'DISQUALIFIED' | 'APPLIED' | 'SKIPPED';
  match_score: number;
  eligibility_verdict?: Record<string, any>;
  missing_skills: string[];
  created_at: string;
}

export interface BulletDiff {
  section: string;
  original_bullet: string;
  suggested_bullet: string;
  change_type: 'REPLACE' | 'ADD' | 'EMPHASIZE';
  reason: string;
}

export interface WSMatchAlertPayload {
  internship: Internship;
  resume_version_id: string;
  match_score: number;
  summary_verdict: string;
  missing_skills: string[];
  tailored_headline: string;
  tailored_summary: string;
  bullet_diffs: BulletDiff[];
  cover_letter: string;
  assessment_answers: Record<string, string>;
}

export interface ApplicationProgressEvent {
  application_id: string;
  status: 'QUEUED' | 'IN_PROGRESS' | 'SUBMITTED' | 'FAILED';
  message: string;
}

export type WebSocketMessage = 
  | { type: 'NEW_MATCH_ALERT'; payload: WSMatchAlertPayload }
  | { type: 'APPLICATION_PROGRESS'; payload: ApplicationProgressEvent };
