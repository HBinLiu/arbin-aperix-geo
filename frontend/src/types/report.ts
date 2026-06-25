export type BrandReportParams = {
  start_date: string;
  end_date: string;
  entity_id?: string;
  platform?: string[];
  topic_id?: string[];
};

export type BrandReportExportUsage = {
  export_count: number;
  export_limit: number | null;
  remaining: number | null;
};
