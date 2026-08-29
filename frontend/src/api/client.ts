import {
  MultiVideoResearchResult,
  ResearchDepth,
  SearchResponse,
  TranscriptResult,
  TranscriptSearchMatch,
  VideoOverview,
} from '../types';

let serverBaseUrl = '';

export const setServerBaseUrl = (url: string) => {
  serverBaseUrl = url.replace(/\/+$/, '');
};

export const getServerBaseUrl = () => {
  return serverBaseUrl || window.location.origin;
};

const request = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const base = serverBaseUrl || '';
  const url = `${base}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`API Error ${res.status}: ${errText}`);
  }

  return res.json();
};

export const api = {
  // Deep Research
  researchTopic: (
    query: string,
    depth: ResearchDepth = 'standard',
    maxVideosPerChannel = 2,
    language = 'en',
    fallbackLanguage = 'en'
  ): Promise<MultiVideoResearchResult> => {
    return request<MultiVideoResearchResult>('/api/research', {
      method: 'POST',
      body: JSON.stringify({
        query,
        depth,
        max_videos_per_channel: maxVideosPerChannel,
        language,
        fallback_language: fallbackLanguage,
      }),
    });
  },

  // Search Videos
  searchVideos: (
    query: string,
    maxResults = 10,
    language = 'en',
    publishedAfter?: string,
    publishedBefore?: string
  ): Promise<SearchResponse> => {
    return request<SearchResponse>('/api/search', {
      method: 'POST',
      body: JSON.stringify({
        query,
        max_results: maxResults,
        language,
        published_after: publishedAfter,
        published_before: publishedBefore,
      }),
    });
  },

  // Video Overview
  getVideo: (videoId: string): Promise<VideoOverview> => {
    return request<VideoOverview>('/api/video', {
      method: 'POST',
      body: JSON.stringify({ video_id: videoId }),
    });
  },

  // Transcript
  getTranscript: (
    videoId: string,
    language = 'en',
    fallbackLanguage = 'en',
    includeTimestamps = true
  ): Promise<TranscriptResult> => {
    return request<TranscriptResult>('/api/transcript', {
      method: 'POST',
      body: JSON.stringify({
        video_id: videoId,
        language,
        fallback_language: fallbackLanguage,
        include_timestamps: includeTimestamps,
      }),
    });
  },

  // In-Video Pinpoint Semantic Search
  findInVideo: (
    videoId: string,
    query: string,
    maxResults = 5,
    language = 'en'
  ): Promise<{ status: string; video_id: string; matches: TranscriptSearchMatch[] }> => {
    return request<{ status: string; video_id: string; matches: TranscriptSearchMatch[] }>(
      '/api/find_in_video',
      {
        method: 'POST',
        body: JSON.stringify({
          video_id: videoId,
          query,
          max_results: maxResults,
          language,
        }),
      }
    );
  },

  // Health check
  checkHealth: async (): Promise<{ status: string; version: string; name: string }> => {
    return request<{ status: string; version: string; name: string }>('/');
  },
};
