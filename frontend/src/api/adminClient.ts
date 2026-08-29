import { getServerBaseUrl } from './client';

export interface AdminConfig {
  [key: string]: any;
}

export interface CacheEntry {
  key: string;
  is_negative: boolean;
  expires_in_seconds: number;
  created_at: number;
  size_bytes: number;
}

export interface ProviderHealthReport {
  provider_name: string;
  is_healthy: boolean;
  capabilities: Record<
    string,
    {
      state: string;
      success_rate: number;
      total_requests: number;
      failure_count: number;
      avg_latency_ms: number;
      last_failure?: string | null;
    }
  >;
  total_requests: number;
  success_rate: number;
  avg_latency_ms: number;
  last_failure_reason?: string | null;
}

export interface AdminMetrics {
  requests: Record<string, number>;
  cache: {
    hits: number;
    misses: number;
    negative_hits: number;
    hit_rate_pct: number;
  };
  single_flight_coalesced_savings: number;
  retrieval: {
    total_queries: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
  };
}

const adminRequest = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const base = getServerBaseUrl() || '';
  const res = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Admin API Error ${res.status}: ${err}`);
  }

  return res.json();
};

export const adminApi = {
  getConfig: (): Promise<{ status: string; config: AdminConfig }> => {
    return adminRequest<{ status: string; config: AdminConfig }>('/api/admin/config');
  },

  getMetrics: (): Promise<{ status: string; metrics: AdminMetrics }> => {
    return adminRequest<{ status: string; metrics: AdminMetrics }>('/api/admin/metrics');
  },

  getCacheKeys: (): Promise<{ status: string; total: number; entries: CacheEntry[] }> => {
    return adminRequest<{ status: string; total: number; entries: CacheEntry[] }>(
      '/api/admin/cache/keys'
    );
  },

  purgeCache: (): Promise<{ status: string; purged_count: number }> => {
    return adminRequest<{ status: string; purged_count: number }>('/api/admin/cache/purge', {
      method: 'POST',
    });
  },

  clearCache: (): Promise<{ status: string; message: string }> => {
    return adminRequest<{ status: string; message: string }>('/api/admin/cache/clear', {
      method: 'POST',
    });
  },

  getCircuits: (): Promise<{ status: string; reports: ProviderHealthReport[] }> => {
    return adminRequest<{ status: string; reports: ProviderHealthReport[] }>(
      '/api/admin/circuits'
    );
  },

  resetCircuits: (): Promise<{ status: string; message: string }> => {
    return adminRequest<{ status: string; message: string }>('/api/admin/circuits/reset', {
      method: 'POST',
    });
  },
};
