import { DocumentOut, VersionOut, DeviceOut, SyncOp, SyncResult } from '../types';

const BASE_URL = '';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(errorJson.error || errorJson.detail?.error || errorJson.detail || 'SyncLab API request failed');
  }
  return res.json();
}

export async function getDocuments(q?: string, tag?: string): Promise<DocumentOut[]> {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (tag) params.set('tag', tag);
  const res = await fetch(`${BASE_URL}/documents?${params.toString()}`);
  return handleResponse<DocumentOut[]>(res);
}

export async function createDocument(payload: {
  title: string;
  body: string;
  collection?: string;
  tags?: string[];
  meta?: Record<string, any>;
  device_id: string;
}): Promise<DocumentOut> {
  const res = await fetch(`${BASE_URL}/documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      collection: payload.collection || 'notes',
      title: payload.title,
      body: payload.body,
      tags: payload.tags || ['offline-first', 'synclab'],
      meta: payload.meta || { app: 'SyncLab Studio' },
      device_id: payload.device_id,
    }),
  });
  return handleResponse<DocumentOut>(res);
}

export async function getDocument(id: number): Promise<DocumentOut> {
  const res = await fetch(`${BASE_URL}/documents/${id}`);
  return handleResponse<DocumentOut>(res);
}

export async function getDocumentVersions(id: number): Promise<VersionOut[]> {
  const res = await fetch(`${BASE_URL}/documents/${id}/versions`);
  return handleResponse<VersionOut[]>(res);
}

export async function restoreDocumentVersion(
  id: number,
  version: number,
  deviceId: string
): Promise<DocumentOut> {
  const res = await fetch(`${BASE_URL}/documents/${id}/restore/${version}?device_id=${encodeURIComponent(deviceId)}`, {
    method: 'POST',
  });
  return handleResponse<DocumentOut>(res);
}

export async function exportMarkdownText(id: number): Promise<string> {
  const res = await fetch(`${BASE_URL}/documents/${id}/export.md`);
  if (!res.ok) throw new Error('Markdown export failed');
  return res.text();
}

export async function executeSync(op: SyncOp): Promise<SyncResult> {
  const res = await fetch(`${BASE_URL}/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(op),
  });
  return handleResponse<SyncResult>(res);
}

export async function getDevices(): Promise<DeviceOut[]> {
  const res = await fetch(`${BASE_URL}/devices`);
  return handleResponse<DeviceOut[]>(res);
}

export async function registerDevice(deviceId: string, name: string): Promise<DeviceOut> {
  const res = await fetch(`${BASE_URL}/devices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_id: deviceId, name }),
  });
  return handleResponse<DeviceOut>(res);
}
