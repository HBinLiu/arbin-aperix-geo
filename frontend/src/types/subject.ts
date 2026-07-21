export type Subject = {
  id: string;
  type: string;
  domain: string;
  brand: string;
  website_url: string;
  aliases: string[];
  summary: string;
  profile_summary: string;
  sampling_platforms?: string[];
  sampling_frequency?: string;
  sampling_enabled?: boolean;
  last_sampled_at: string;
  tenant_id?: string;
  created_at?: string;
  updated_at?: string;
};
