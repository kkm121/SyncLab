import React, { useState, useEffect } from 'react';
import { getDevices, registerDevice } from '../lib/api';
import { sounds } from '../lib/sound';
import { DeviceOut } from '../types';
import {
  DatabaseIcon,
  LaptopIcon,
  SmartphoneIcon,
  PlusIcon,
  CheckCircleIcon,
  ClockIcon,
  RefreshCwIcon,
} from './Icons';

interface Props {
  flashNotice: (msg: string) => void;
}

export const DeviceFleet: React.FC<Props> = ({ flashNotice }) => {
  const [devices, setDevices] = useState<DeviceOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  const [registering, setRegistering] = useState(false);

  const fetchDeviceList = async () => {
    setLoading(true);
    try {
      const data = await getDevices();
      setDevices(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeviceList();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDeviceId.trim() || !newDeviceName.trim()) return;
    setRegistering(true);
    sounds.playTap();
    try {
      await registerDevice(newDeviceId.trim(), newDeviceName.trim());
      sounds.playSuccess();
      flashNotice(`Device ${newDeviceName} registered into sync cluster.`);
      setNewDeviceId('');
      setNewDeviceName('');
      fetchDeviceList();
    } catch (err: any) {
      flashNotice(err.message || 'Registration failed');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="devices-fleet-container">
      <section className="dropbox-hero">
        <div className="hero-kicker-strip">
          <span className="hero-kicker-beacon" />
          <span className="hero-kicker">DISTRIBUTED NODE TOPOLOGY</span>
        </div>
        <h2 className="hero-heading">Device Fleet & Peer Telemetry</h2>
        <p className="hero-tagline">
          Monitor peer nodes synchronizing across local offline buffers. Register workstations and mobile nodes with independent sync cursors.
        </p>
      </section>

      {/* Register Node Form */}
      <form className="register-device-bar glass-panel" onSubmit={handleRegister}>
        <div className="register-inputs-row">
          <div className="reg-field">
            <label className="section-label">NODE IDENTIFIER</label>
            <input
              type="text"
              className="mod-search-input"
              placeholder="e.g. client-macbook-pro"
              value={newDeviceId}
              onChange={(e) => setNewDeviceId(e.target.value)}
              required
            />
          </div>

          <div className="reg-field">
            <label className="section-label">FRIENDLY DEVICE NAME</label>
            <input
              type="text"
              className="mod-search-input"
              placeholder="e.g. Lead Engineer Laptop"
              value={newDeviceName}
              onChange={(e) => setNewDeviceName(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="btn-primary" disabled={registering} style={{ alignSelf: 'flex-end', height: '42px' }}>
            <PlusIcon size={14} />
            <span>{registering ? 'Registering...' : 'Register Peer Node'}</span>
          </button>
        </div>
      </form>

      {/* Devices Grid */}
      <div className="devices-cards-grid">
        {loading ? (
          <div className="loading-state-scanner" style={{ gridColumn: '1 / -1' }}>
            <RefreshCwIcon size={24} className="spin-slow" />
            <span>Discovering network devices...</span>
          </div>
        ) : devices.length === 0 ? (
          <div className="empty-state-luxury glass-panel" style={{ gridColumn: '1 / -1' }}>
            <DatabaseIcon size={36} />
            <h4 className="empty-state-title">No Peer Nodes Registered Yet</h4>
            <p className="empty-state-desc">Register client devices to monitor sync cursors and offline vectors.</p>
          </div>
        ) : (
          devices.map((dev) => (
            <div key={dev.device_id} className="device-node-card glass-panel">
              <div className="dev-node-top">
                <div className="dev-icon-wrap">
                  {dev.device_id.includes('mobile') || dev.device_id.includes('phone') ? (
                    <SmartphoneIcon size={22} />
                  ) : (
                    <LaptopIcon size={22} />
                  )}
                </div>
                <div>
                  <h4 className="dev-node-name">{dev.name}</h4>
                  <span className="dev-node-id">{dev.device_id}</span>
                </div>
              </div>

              <div className="dev-node-telemetry">
                <div className="telemetry-row">
                  <ClockIcon size={12} />
                  <span>Last Sync: {dev.last_seen ? new Date(dev.last_seen).toLocaleTimeString() : 'Active Now'}</span>
                </div>
                <div className="telemetry-row">
                  <CheckCircleIcon size={12} className="highlight-green" />
                  <span>Status: Synchronized with Server Head</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
