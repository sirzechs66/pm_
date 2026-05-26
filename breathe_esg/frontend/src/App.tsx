import { useEffect, useState } from 'react';

import {
  approveActivity,
  fetchActivities,
  fetchRawData,
  retryActivity,
  setTenantContext,
  updateActivityScope,
  uploadSourceFile,
  type ActivityData,
  type RawRowResponse,
} from './shared/api/client';

const analystName = 'Primary Analyst';
const sourceOptions = ['all', 'utility', 'travel', 'sap'] as const;
const statusOptions = ['all', 'pending_review', 'approved', 'failed'] as const;
const suspiciousOptions = ['all', 'true', 'false'] as const;

function formatDate(value: string | null) {
  if (!value) {
    return 'N/A';
  }
  return new Date(value).toLocaleString();
}

function StatusPill({ value }: { value: string }) {
  return <span className={`pill pill-${value.replace(/_/g, '-')}`}>{value.replace(/_/g, ' ')}</span>;
}

function ScopeSelect({ value, onChange }: { value: number | null; onChange: (scope: 1 | 2 | 3) => void }) {
  return (
    <select value={value ?? ''} onChange={(event) => onChange(Number(event.target.value) as 1 | 2 | 3)}>
      <option value="" disabled>
        Select
      </option>
      <option value="1">Scope 1</option>
      <option value="2">Scope 2</option>
      <option value="3">Scope 3</option>
    </select>
  );
}

export default function App() {
  const [tenantId, setTenantId] = useState(1);
  const [activities, setActivities] = useState<ActivityData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sourceFilter, setSourceFilter] = useState<(typeof sourceOptions)[number]>('all');
  const [statusFilter, setStatusFilter] = useState<(typeof statusOptions)[number]>('all');
  const [suspiciousFilter, setSuspiciousFilter] = useState<(typeof suspiciousOptions)[number]>('all');
  const [uploadSource, setUploadSource] = useState<'utility' | 'travel' | 'sap'>('utility');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [selectedRaw, setSelectedRaw] = useState<RawRowResponse | null>(null);
  const [modalError, setModalError] = useState('');

  async function loadActivities() {
    setLoading(true);
    setError('');
    setTenantContext(tenantId, analystName);
    try {
      const data = await fetchActivities({
        source_type: sourceFilter === 'all' ? undefined : sourceFilter,
        status: statusFilter === 'all' ? undefined : statusFilter,
        suspicious_flag: suspiciousFilter === 'all' ? undefined : suspiciousFilter,
      });
      setActivities(data);
    } catch {
      setError('Backend connection failed. Make sure Django is running and migrations are applied.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadActivities();
  }, [tenantId, sourceFilter, statusFilter, suspiciousFilter]);

  const failedCount = activities.filter((activity) => activity.status === 'failed').length;
  const pendingCount = activities.filter((activity) => activity.status === 'pending_review').length;
  const suspiciousCount = activities.filter((activity) => activity.suspicious_flag).length;

  async function handleUpload() {
    if (!uploadFile) {
      setError('Choose a file before uploading.');
      return;
    }
    setTenantContext(tenantId, analystName);
    setError('');
    try {
      await uploadSourceFile(uploadSource, uploadFile);
      setUploadFile(null);
      const input = document.getElementById('upload-input') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }
      await loadActivities();
    } catch {
      setError('Upload failed. Check that the file matches the expected source format.');
    }
  }

  async function handleApprove(id: number) {
    setTenantContext(tenantId, analystName);
    await approveActivity(id);
    await loadActivities();
  }

  async function handleScopeChange(id: number, scope: 1 | 2 | 3) {
    setTenantContext(tenantId, analystName);
    await updateActivityScope(id, scope);
    await loadActivities();
  }

  async function handleRetry(id: number) {
    setTenantContext(tenantId, analystName);
    try {
      await retryActivity(id);
      await loadActivities();
    } catch {
      setError('Retry failed. The raw row still does not contain enough data to normalize.');
    }
  }

  async function handleViewRaw(id: number) {
    setTenantContext(tenantId, analystName);
    setModalError('');
    try {
      setSelectedRaw(await fetchRawData(id));
    } catch {
      setModalError('Could not load raw row.');
    }
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Breathe ESG Prototype</p>
          <h1>Tenant-scoped activity review and normalization</h1>
          <p className="hero-copy">
            Upload utility, travel, and SAP source files, normalize them into one activity queue, and review suspicious or failed records in place.
          </p>
        </div>
        <div className="hero-meta">
          <label className="meta-block">
            <span>Tenant ID</span>
            <input type="number" min="1" value={tenantId} onChange={(event) => setTenantId(Number(event.target.value) || 1)} />
          </label>
          <div className="meta-block">
            <span>Analyst</span>
            <strong>{analystName}</strong>
          </div>
        </div>
      </header>

      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-label">Activities</span>
          <strong>{activities.length}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Pending review</span>
          <strong>{pendingCount}</strong>
        </article>
        <article className="metric-card">
          <span className="metric-label">Failed rows</span>
          <strong>{failedCount}</strong>
        </article>
        <article className="metric-card metric-card-alert">
          <span className="metric-label">Suspicious</span>
          <strong>{suspiciousCount}</strong>
        </article>
      </section>

      <section className="toolbar panel">
        <div className="toolbar-row">
          <div className="field-group">
            <label>Source</label>
            <select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value as (typeof sourceOptions)[number])}>
              {sourceOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="field-group">
            <label>Status</label>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as (typeof statusOptions)[number])}>
              {statusOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div className="field-group">
            <label>Suspicious</label>
            <select value={suspiciousFilter} onChange={(event) => setSuspiciousFilter(event.target.value as (typeof suspiciousOptions)[number])}>
              {suspiciousOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="toolbar-row upload-row">
          <div className="field-group">
            <label>Upload source</label>
            <select value={uploadSource} onChange={(event) => setUploadSource(event.target.value as 'utility' | 'travel' | 'sap')}>
              <option value="utility">utility</option>
              <option value="travel">travel</option>
              <option value="sap">sap</option>
            </select>
          </div>
          <input id="upload-input" type="file" accept={uploadSource === 'travel' ? '.json' : '.csv'} onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
          <button onClick={() => void handleUpload()}>Upload file</button>
        </div>
      </section>

      {error ? <section className="error-banner">{error}</section> : null}
      {loading ? <p className="loading-state">Loading activities...</p> : null}

      <section className="panel">
        <div className="panel-header">
          <h2>Review queue</h2>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th>Description</th>
                <th>Quantity</th>
                <th>Scope</th>
                <th>Status</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {activities.map((activity) => (
                <tr key={activity.id} className={activity.suspicious_flag ? 'row-suspicious' : activity.status === 'failed' ? 'row-failed' : ''}>
                  <td>{activity.date ?? 'N/A'}</td>
                  <td>{activity.source_type}</td>
                  <td>
                    <strong>{activity.description}</strong>
                    {activity.failure_reason ? <p className="inline-detail">{activity.failure_reason}</p> : null}
                    {activity.audits.length > 0 ? <p className="inline-detail">Last audit: {activity.audits[0].action} by {activity.audits[0].actor}</p> : null}
                  </td>
                  <td>{activity.quantity} {activity.unit_normalised}</td>
                  <td><ScopeSelect value={activity.scope} onChange={(scope) => void handleScopeChange(activity.id, scope)} /></td>
                  <td>
                    <StatusPill value={activity.status} />
                    {activity.suspicious_flag ? <span className="flag-chip">Suspicious</span> : null}
                  </td>
                  <td className="action-cell">
                    <button onClick={() => void handleViewRaw(activity.id)}>Raw</button>
                    <button disabled={activity.status === 'approved'} onClick={() => void handleApprove(activity.id)}>Approve</button>
                    {activity.status === 'failed' ? <button onClick={() => void handleRetry(activity.id)}>Retry</button> : null}
                  </td>
                </tr>
              ))}
              {activities.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">No activities for the current filters.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      {selectedRaw ? (
        <section className="modal-backdrop" onClick={() => setSelectedRaw(null)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>Raw row</h3>
              <button onClick={() => setSelectedRaw(null)}>Close</button>
            </div>
            {modalError ? <p className="error-banner">{modalError}</p> : null}
            <p className="inline-detail">Status: {selectedRaw.status}</p>
            <pre>{JSON.stringify(selectedRaw.raw_data, null, 2)}</pre>
          </div>
        </section>
      ) : null}
    </div>
  );
}
