export type ResearchDepth = 'quick' | 'standard' | 'deep';

export interface SourceCitation {
  video_id: string;
  video_title: string;
  channel: string;
  start_seconds: number;
  end_seconds: number;
  time_range: string;
  url_with_timestamp: string;
  quote: string;
  relevance: number;
  language?: string;
}

export interface VideoResearchSummary {
  video_id: string;
  title: string;
  channel: string;
  url: string;
  duration?: string;
  caption_found: boolean;
  language?: string;
  key_citations: SourceCitation[];
}

export interface ClaimEvidenceCluster {
  cluster_id: string;
  topic_headline: string;
  independent_sources_count: number;
  consensus_score: number;
  channels: string[];
  citations: SourceCitation[];
}

export interface MultiVideoResearchResult {
  topic: string;
  depth: ResearchDepth;
  total_videos_analyzed: number;
  videos_with_transcripts: number;
  total_evidence_chunks: number;
  sources: VideoResearchSummary[];
  evidence_clusters: ClaimEvidenceCluster[];
  all_citations_ranked: SourceCitation[];
}

export interface TranscriptSearchMatch {
  chunk_id: string | number;
  video_id: string;
  time_range: string;
  start_seconds: number;
  end_seconds: number;
  relevance_score: number;
  text: string;
  url: string;
  chapter_title?: string;
  language?: string;
}

export interface Chapter {
  title: string;
  start_seconds: number;
  end_seconds?: number;
  timestamp_formatted: string;
  url: string;
}

export interface VideoOverview {
  video_id: string;
  title: string;
  channel: string;
  channel_id?: string;
  published_date?: string;
  duration_seconds?: number;
  duration_formatted: string;
  view_count?: number;
  description?: string;
  tags: string[];
  chapters: Chapter[];
  caption_available: boolean;
  available_languages: string[];
  url: string;
  thumbnail_url?: string;
}

export interface VideoSearchResult {
  video_id: string;
  title: string;
  channel: string;
  channel_id?: string;
  duration?: string;
  duration_seconds?: number;
  view_count?: string;
  view_count_num?: number;
  published_time?: string;
  description_snippet?: string;
  url: string;
  thumbnail?: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: VideoSearchResult[];
}

export interface TranscriptResult {
  video_id: string;
  language: string;
  requested_language: string;
  actual_language: string;
  fallback_used: boolean;
  fallback_language?: string;
  is_generated: boolean;
  is_translated: boolean;
  total_segments: number;
  total_words: number;
  duration_seconds: number;
  segments: Array<{
    start: number;
    duration: number;
    end: number;
    text: string;
    timestamp_formatted: string;
    url: string;
  }>;
  full_text: string;
}
