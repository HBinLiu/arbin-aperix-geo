export type MonitoringScope = {
  region: string;
  language: string;
  note?: string | null;
};

export type Subject = {
  id: string;
  type: string;
  domain: string;
  brand: string;
  website_url: string;
  aliases: string[];
  monitoring_scope: MonitoringScope;
  profile_summary: string;
  sampling_platforms?: string[];
  sampling_interval?: number;
  last_sampled_at: string;
  tenant_id?: string;
  created_at?: string;
  updated_at?: string;
};
