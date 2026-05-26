import axios from 'axios';

export interface ActivityAudit {
  id: number;
  action: string;
  previous_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  actor: string;
  created_at: string;
}

export interface ActivityData {
  id: number;
  tenant_id: number;
  source_type: 'utility' | 'travel' | 'sap';
  date: string | null;
  quantity: string;
  unit_normalised: string;
  description: string;
  scope: 1 | 2 | 3 | null;
  status: 'pending_review' | 'approved' | 'failed';
  suspicious_flag: boolean;
  failure_reason: string;
  raw_data_link: string;
  created_at: string;
  updated_at: string;
  approved_by: string;
  approved_at: string | null;
  modified_by: string;
  previous_scope: number | null;
  previous_status: string;
  audits: ActivityAudit[];
}

export interface UploadResponse {
  batch_id: number;
  source_type: string;
  count: number;
  results: ActivityData[];
}

export interface RawRowResponse {
  id: number;
  source_type: string;
  status: string;
  failure_reason: string;
  row_index: number;
  raw_data: Record<string, unknown>;
}

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export function setTenantContext(tenantId: number, analystName: string) {
  api.defaults.headers.common['X-Tenant-Id'] = String(tenantId);
  api.defaults.headers.common['X-Analyst-Name'] = analystName;
}

export async function fetchActivities(params?: {
  source_type?: string;
  status?: string;
  suspicious_flag?: string;
}): Promise<ActivityData[]> {
  const response = await api.get<ActivityData[]>('/activities/', { params });
  return response.data;
}

export async function uploadSourceFile(sourceType: 'utility' | 'travel' | 'sap', file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>(`/upload/${sourceType}/`, formData);
  return response.data;
}

export async function approveActivity(id: number): Promise<ActivityData> {
  const response = await api.post<ActivityData>(`/activities/${id}/approve/`);
  return response.data;
}

export async function updateActivityScope(id: number, scope: 1 | 2 | 3): Promise<ActivityData> {
  const response = await api.patch<ActivityData>(`/activities/${id}/`, { scope });
  return response.data;
}

export async function retryActivity(id: number): Promise<ActivityData> {
  const response = await api.patch<ActivityData>(`/activities/${id}/`, { action: 'retry' });
  return response.data;
}

export async function fetchRawData(id: number): Promise<RawRowResponse> {
  const response = await api.get<RawRowResponse>(`/activities/${id}/raw/`);
  return response.data;
}
