import React, { useState, useEffect } from 'react';
import {
  getDocuments,
  createDocument,
  getDocument,
  getDocumentVersions,
  restoreDocumentVersion,
  executeSync,
} from '../lib/api';
import { sounds } from '../lib/sound';
import { DocumentOut, VersionOut } from '../types';
import {
  FileTextIcon,
  PlusIcon,
  SearchIcon,
  RotateCwIcon,
  CheckCircleIcon,
  TagIcon,
  ClockIcon,
  DownloadIcon,
  GitMergeIcon,
  DatabaseIcon,
  SparklesIcon,
} from './Icons';

interface Props {
  flashNotice: (msg: string) => void;
  onOpenObsidianExport: (docId: number) => void;
}

export const DocumentStudio: React.FC<Props> = ({ flashNotice, onOpenObsidianExport }) => {
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentOut | null>(null);
  const [versions, setVersions] = useState<VersionOut[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Active Edit Form
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editTags, setEditTags] = useState('');

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await getDocuments(searchQuery || undefined);
      setDocuments(data);
      if (!selectedDoc && data.length > 0) {
        handleSelectDoc(data[0]);
      } else if (selectedDoc) {
        const refreshed = data.find((d) => d.id === selectedDoc.id);
        if (refreshed) {
          setSelectedDoc(refreshed);
          setEditTitle(refreshed.title);
          setEditBody(refreshed.body);
          setEditTags(refreshed.tags.join(', '));
        }
      }
    } catch (err: any) {
      flashNotice(err.message || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [searchQuery]);

  const handleSelectDoc = async (doc: DocumentOut) => {
    sounds.playTap();
    setSelectedDoc(doc);
    setEditTitle(doc.title);
    setEditBody(doc.body);
    setEditTags(doc.tags.join(', '));
    setIsFlipped(false);
    try {
      const v = await getDocumentVersions(doc.id);
      setVersions(v);
    } catch {
      /* ignore */
    }
  };

  const handleCreateNew = async () => {
    sounds.playTap();
    try {
      const doc = await createDocument({
        title: 'Untitled Collaborative Draft',
        body: '# SyncLab Document\n\nThis note is tracked with versioned writes and 3-way merge.\n\n- Line A: Local-first architecture\n- Line B: Zero silent overwrite guarantee\n- Line C: Obsidian markdown compatible',
        collection: 'notes',
        tags: ['draft', 'offline-first'],
        device_id: 'client-desktop-alpha',
      });
      sounds.playSuccess();
      flashNotice('New document created.');
      await fetchDocs();
      handleSelectDoc(doc);
    } catch (err: any) {
      flashNotice(err.message || 'Creation failed');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDoc) return;
    setSaving(true);
    sounds.playTap();
    try {
      const parsedTags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
      const res = await executeSync({
        device_id: 'client-desktop-alpha',
        document_id: selectedDoc.id,
        base_version: selectedDoc.version,
        title: editTitle.trim(),
        body: editBody,
        tags: parsedTags,
        strategy: 'diff3',
      });

      if (res.outcome === 'accepted' || res.outcome === 'merged') {
        sounds.playSuccess();
        flashNotice(`Document synchronized successfully (Version ${res.target_version} - ${res.outcome}).`);
      } else if (res.outcome === 'conflict') {
        sounds.playConflict();
        flashNotice(`Concurrent write detected! Conflict recorded explicitly: ${res.resolution}`);
      }

      await fetchDocs();
      if (selectedDoc) {
        const v = await getDocumentVersions(selectedDoc.id);
        setVersions(v);
      }
    } catch (err: any) {
      sounds.playConflict();
      flashNotice(err.message || 'Sync failed');
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = async (versionNum: number) => {
    if (!selectedDoc) return;
    sounds.playTap();
    try {
      const restored = await restoreDocumentVersion(selectedDoc.id, versionNum, 'client-desktop-alpha');
      sounds.playSuccess();
      flashNotice(`Restored to Version ${versionNum} as new Version ${restored.version}.`);
      await fetchDocs();
      handleSelectDoc(restored);
    } catch (err: any) {
      flashNotice(err.message || 'Restore failed');
    }
  };

  return (
    <div className="document-studio-container">
      {/* Telemetry Header */}
      <section className="mod-telemetry-grid">
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">ACTIVE VAULT DOCUMENTS</span>
          <strong className="telemetry-val">{documents.length}</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">CURRENT REVISION</span>
          <strong className="telemetry-val highlight-green">v{selectedDoc?.version || 1}</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">VERSION HISTORY DEPTH</span>
          <strong className="telemetry-val highlight-indigo">{versions.length} Revisions</strong>
        </div>
        <div className="telemetry-box glass-panel">
          <span className="telemetry-lbl">SYNC ENGINE PROTOCOL</span>
          <strong className="telemetry-val highlight-amber">3-WAY DIFF3</strong>
        </div>
      </section>

      {/* Main Split Layout */}
      <div className="cases-split-layout">
        {/* Document Sidebar */}
        <div className="cases-list-card glass-panel doc-sidebar-panel">
          <div className="doc-sidebar-header">
            <div className="search-input-wrap">
              <SearchIcon size={14} className="search-icon-field" />
              <input
                type="text"
                className="mod-search-input doc-search-input"
                placeholder="Search notes & tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            <button className="btn-primary btn-new-doc" onClick={handleCreateNew}>
              <PlusIcon size={14} />
              <span>New Doc</span>
            </button>
          </div>

          <div className="doc-items-list">
            {loading ? (
              <div className="empty-state-desc" style={{ padding: '24px', textAlign: 'center' }}>
                Loading documents...
              </div>
            ) : documents.length === 0 ? (
              <div className="empty-state-luxury" style={{ padding: '36px 20px' }}>
                <FileTextIcon size={32} />
                <h4 className="empty-state-title" style={{ fontSize: '15px', marginTop: '10px' }}>
                  No Documents Found
                </h4>
                <p className="empty-state-desc" style={{ fontSize: '12px' }}>
                  Create your first offline-synced note to begin.
                </p>
                <button className="btn-primary" onClick={handleCreateNew}>
                  <PlusIcon size={14} />
                  <span>Create Note</span>
                </button>
              </div>
            ) : (
              documents.map((d) => (
                <div
                  key={d.id}
                  className={`doc-list-item ${selectedDoc?.id === d.id ? 'active' : ''}`}
                  onClick={() => handleSelectDoc(d)}
                >
                  <div className="doc-item-top">
                    <span className="doc-item-title">{d.title || 'Untitled Document'}</span>
                    <span className="doc-version-badge">v{d.version}</span>
                  </div>
                  <p className="doc-item-preview">{d.body.slice(0, 60)}...</p>
                  <div className="doc-item-tags">
                    {d.tags.map((t, idx) => (
                      <span key={idx} className="doc-tag-pill">
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 3D Flip Editor Stage */}
        <div className="perspective-flip-stage doc-editor-stage">
          <div className={`flip-card-3d ${isFlipped ? 'is-flipped' : ''}`}>
            
            {/* FRONT FACE: Document Editor */}
            <div className="flip-card-face flip-card-front">
              {selectedDoc ? (
                <form className="dropbox-main-card glass-panel" onSubmit={handleSave}>
                  <div className="card-top-action-bar">
                    <div className="card-header-bar">
                      <span className="step-num-badge">DOC</span>
                      <div>
                        <h3 className="card-section-title">Collaborative Document Canvas</h3>
                        <p className="card-section-desc">Version {selectedDoc.version} · Offline sync with zero data loss</p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => onOpenObsidianExport(selectedDoc.id)}
                        title="Export document with Obsidian YAML frontmatter and backlinks"
                      >
                        <DownloadIcon size={14} />
                        <span>Obsidian Export</span>
                      </button>

                      <button
                        type="button"
                        className="card-flip-btn"
                        onClick={() => {
                          sounds.playTap();
                          setIsFlipped(true);
                        }}
                        title="3D Flip to inspect 3-Way diff matrix and merge engine"
                      >
                        <RotateCwIcon size={14} />
                        <span>3D Flip · Merge Inspector</span>
                      </button>
                    </div>
                  </div>

                  {/* Title & Tags */}
                  <div className="doc-fields-grid">
                    <div className="field-group">
                      <label className="section-label">DOCUMENT TITLE</label>
                      <input
                        type="text"
                        className="mod-search-input"
                        style={{ width: '100%', fontSize: '15px', fontWeight: '700' }}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        required
                      />
                    </div>

                    <div className="field-group">
                      <label className="section-label">OBSIDIAN TAGS (COMMA-SEPARATED)</label>
                      <input
                        type="text"
                        className="mod-search-input"
                        style={{ width: '100%' }}
                        value={editTags}
                        onChange={(e) => setEditTags(e.target.value)}
                        placeholder="research, architecture, sprint"
                      />
                    </div>
                  </div>

                  {/* Body Editor */}
                  <div className="textarea-wrapper" style={{ marginTop: '16px' }}>
                    <label className="section-label">MARKDOWN CONTENT</label>
                    <textarea
                      className="incident-textarea"
                      rows={13}
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      placeholder="Write your document content here in Markdown format..."
                      required
                    />
                    <div className="textarea-footer">
                      <span>{editBody.length} characters · {editBody.split('\n').length} lines</span>
                      <span className="ml-analyzing-indicator">
                        <CheckCircleIcon size={13} />
                        <span>Base Version v{selectedDoc.version} locked</span>
                      </span>
                    </div>
                  </div>

                  {/* Save & Telemetry Row */}
                  <div className="form-submit-row">
                    <div className="anonymity-pledge-note">
                      <GitMergeIcon size={16} />
                      <span>Sync engine computes diff3 line-level deltas before committing revision.</span>
                    </div>

                    <button type="submit" className="submit-report-btn" disabled={saving}>
                      <RefreshCwIcon size={15} className={saving ? 'spin-slow' : ''} />
                      <span>{saving ? 'Synchronizing Deliberately...' : 'Save & Sync Revision →'}</span>
                    </button>
                  </div>

                  {/* Version History Timeline */}
                  <div className="doc-history-drawer" style={{ marginTop: '24px' }}>
                    <span className="section-label">IMMUTABLE REVISION HISTORY ({versions.length})</span>
                    <div className="versions-timeline-horizontal">
                      {versions.map((v) => (
                        <div key={v.version} className="version-history-chip">
                          <div className="v-chip-top">
                            <span className="v-num">v{v.version}</span>
                            <span className={`v-outcome ${v.outcome}`}>{v.outcome}</span>
                          </div>
                          <span className="v-date">{new Date(v.created_at).toLocaleTimeString()}</span>
                          <span className="v-dev">{v.device_id}</span>
                          {v.version !== selectedDoc.version && (
                            <button
                              type="button"
                              className="v-restore-btn"
                              onClick={() => handleRestore(v.version)}
                              title={`Restore content from revision v${v.version}`}
                            >
                              Restore
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </form>
              ) : (
                <div className="dropbox-main-card glass-panel empty-state-luxury">
                  <FileTextIcon size={44} />
                  <h4 className="empty-state-title">Select a Document</h4>
                  <p className="empty-state-desc">Choose a document from the left vault to begin editing and syncing.</p>
                </div>
              )}
            </div>

            {/* BACK FACE: Visual 3-Way Merge & Sync Conflict Graph */}
            <div className="flip-card-face flip-card-back">
              <div className="dropbox-main-card glass-panel ml-back-panel">
                <div className="card-top-action-bar">
                  <div className="card-header-bar">
                    <span className="step-num-badge">DIFF3</span>
                    <div>
                      <h3 className="card-section-title">Visual 3-Way Merge Engine</h3>
                      <p className="card-section-desc">Ancestor base version, client mutation, and concurrent resolution analysis</p>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="card-flip-btn return-btn"
                    onClick={() => {
                      sounds.playTap();
                      setIsFlipped(false);
                    }}
                    title="Return to document editor"
                  >
                    <RotateCwIcon size={14} />
                    <span>Return to Document Canvas</span>
                  </button>
                </div>

                <div className="diff-matrix-grid">
                  <div className="diff-column glass-panel">
                    <div className="diff-col-header">
                      <ClockIcon size={14} />
                      <span>COMMON ANCESTOR (BASE v{selectedDoc?.version || 1})</span>
                    </div>
                    <pre className="diff-pre">{selectedDoc?.body || 'No base document loaded'}</pre>
                  </div>

                  <div className="diff-column glass-panel">
                    <div className="diff-col-header highlight-cyan">
                      <LaptopIcon size={14} />
                      <span>ACTIVE CLIENT REVISION (STAGING)</span>
                    </div>
                    <pre className="diff-pre">{editBody || 'No active edits'}</pre>
                  </div>
                </div>

                <div className="diff-strategies-card glass-panel" style={{ marginTop: '16px', padding: '16px' }}>
                  <span className="section-label">SYNC RESOLUTION BEHAVIOR</span>
                  <div className="strategy-descriptions-list">
                    <div className="strat-item">
                      <strong>diff3 (Automatic 3-Way Line Merge):</strong>
                      <p>Disjoint non-overlapping line edits are merged seamlessly into a clean target revision.</p>
                    </div>
                    <div className="strat-item">
                      <strong>Explicit Conflict Recording:</strong>
                      <p>If two peers edit the same line, the engine never blindly overwrites; it records a conflict outcome.</p>
                    </div>
                    <div className="strat-item">
                      <strong>Audit Trail:</strong>
                      <p>History is immutable. Every restore or merge commits a monotonically increasing version number.</p>
                    </div>
                  </div>
                </div>

                <div className="ml-back-footer">
                  <span className="ml-engine-badge">SyncLab Distributed Protocol · Diff3 Engine · SQLAlchemy + SQLite</span>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      sounds.playTap();
                      setIsFlipped(false);
                    }}
                  >
                    Return to Editor →
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};
