import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Machine, Site, TelemetryPoint } from '../../types';
import { useFleet } from '../../context/FleetContext';
import { Fuel, BatteryCharging, ShieldAlert, Cpu } from 'lucide-react';

// Custom Map Controller to smoothly fly to selected site
const MapFlyTo: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
};

// Create custom industrial SVG marker pin
const createCustomPin = (label: string, isElectric: boolean, hasAlert: boolean) => {
  const bgColor = hasAlert ? '#EF4444' : isElectric ? '#06B6D4' : '#FFCD11';
  const textColor = hasAlert ? '#FFFFFF' : '#000000';
  
  return L.divIcon({
    className: 'custom-cat-pin',
    html: `
      <div style="
        background: #141518;
        border: 2px solid ${bgColor};
        color: ${textColor};
        border-radius: 6px;
        padding: 2px 6px;
        font-family: monospace;
        font-size: 10px;
        font-weight: 800;
        display: flex;
        align-items: center;
        gap: 3px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.8);
        transform: translate(-50%, -50%);
        white-space: nowrap;
      ">
        <span style="background: ${bgColor}; width: 6px; height: 6px; border-radius: 50%; display: inline-block;"></span>
        <span style="color: #FFFFFF;">${label}</span>
      </div>
    `,
    iconSize: [60, 24],
    iconAnchor: [30, 12],
  });
};

export const FleetMap: React.FC = () => {
  const { machines, sites, alerts, currentTelemetry } = useFleet();
  const [selectedSiteId, setSelectedSiteId] = useState<string>('all');
  const [center, setCenter] = useState<[number, number]>([12.92, 79.1]);
  const [zoom, setZoom] = useState<number>(9);

  // Compute machine pseudo coordinates based on site lat/lon with deterministic jitter
  const getMachineCoords = (machine: Machine): [number, number] => {
    const site = sites.find(s => s.site_id === machine.site_id);
    if (!site) return [12.9010, 80.2279];

    // Simple deterministic offset based on machine_id hash
    const hash = machine.machine_id.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const latOffset = ((hash % 10) - 5) * 0.0035;
    const lonOffset = (((hash * 3) % 10) - 5) * 0.0035;

    return [site.lat + latOffset, site.lon + lonOffset];
  };

  const handleSiteFilter = (siteId: string) => {
    setSelectedSiteId(siteId);
    if (siteId === 'all') {
      setCenter([12.92, 79.1]);
      setZoom(9);
    } else {
      const s = sites.find(item => item.site_id === siteId);
      if (s) {
        setCenter([s.lat, s.lon]);
        setZoom(14);
      }
    }
  };

  const filteredMachines = selectedSiteId === 'all' 
    ? machines 
    : machines.filter(m => m.site_id === selectedSiteId);

  return (
    <div className="bg-cat-panel border border-cat-border rounded-xl p-4 shadow-cat">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cat-border pb-3 mb-3">
        <div className="flex items-center space-x-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cat-yellow animate-pulse" />
          <h3 className="text-sm font-bold font-mono uppercase tracking-wider text-white">
            Live Fleet Geospatial Telemetry
          </h3>
          <span className="text-xs text-slate-400 font-mono">
            ({filteredMachines.length} Active Units Across {sites.length} Regional Sites)
          </span>
        </div>

        {/* Site Switcher Filter Buttons */}
        <div className="flex items-center space-x-1.5 bg-cat-dark p-1 rounded-lg border border-cat-border text-xs">
          <button
            onClick={() => handleSiteFilter('all')}
            className={`px-2.5 py-1 rounded font-mono font-medium transition-colors ${
              selectedSiteId === 'all' ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
            }`}
          >
            All Sites (Tamil Nadu & Karnataka)
          </button>
          {sites.map(site => (
            <button
              key={site.site_id}
              onClick={() => handleSiteFilter(site.site_id)}
              className={`px-2.5 py-1 rounded font-mono font-medium transition-colors ${
                selectedSiteId === site.site_id ? 'bg-cat-yellow text-black font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              {site.city} ({site.site_id})
            </button>
          ))}
        </div>
      </div>

      {/* Map Container */}
      <div className="h-[440px] w-full rounded-lg overflow-hidden border border-cat-border relative shadow-inner">
        <MapContainer
          center={center}
          zoom={zoom}
          scrollWheelZoom={false}
          style={{ height: '100%', width: '100%', background: '#121316' }}
        >
          <MapFlyTo center={center} zoom={zoom} />

          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {filteredMachines.map(machine => {
            const pos = getMachineCoords(machine);
            const isElectric = machine.powertrain === 'electric';
            const machineAlert = alerts.find(a => a.machine_id === machine.machine_id && !a.acknowledged);
            const pinIcon = createCustomPin(machine.machine_id, isElectric, !!machineAlert);

            return (
              <Marker key={machine.machine_id} position={pos} icon={pinIcon}>
                <Popup className="cat-map-popup">
                  <div className="p-1 min-w-[200px] text-xs font-sans text-slate-900">
                    <div className="flex items-center justify-between border-b pb-1 mb-1.5">
                      <span className="font-mono font-bold text-sm text-black">{machine.machine_id}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-800 uppercase font-bold">
                        {machine.powertrain}
                      </span>
                    </div>

                    <div className="font-bold text-slate-800">{machine.reference_model}</div>
                    <div className="text-[11px] text-slate-600 font-mono mt-0.5">
                      Assigned Operator: {machine.primary_operator_id || 'Rotating'}
                    </div>

                    <div className="grid grid-cols-2 gap-1.5 my-2 pt-1 border-t text-[11px] font-mono">
                      <div>Engine Hours:</div>
                      <div className="font-bold">{machine.engine_hours_at_start.toFixed(1)} h</div>
                      <div>Energy Cap:</div>
                      <div className="font-bold">
                        {isElectric ? `${machine.battery_kwh} kWh` : `${machine.fuel_tank_l} L`}
                      </div>
                    </div>

                    {machineAlert && (
                      <div className="p-1.5 rounded bg-rose-100 border border-rose-300 text-rose-800 text-[10px] font-bold mt-1">
                        ⚠️ {machineAlert.alert_code.toUpperCase()}
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* In-Map Legend Overlay */}
        <div className="absolute bottom-3 left-3 z-[1000] bg-cat-dark/95 border border-cat-border px-3 py-2 rounded-lg text-[10px] font-mono shadow-xl backdrop-blur-sm space-y-1">
          <div className="text-slate-400 uppercase font-bold tracking-wider mb-1">Fleet Markers</div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cat-yellow inline-block" />
            <span className="text-slate-200">Diesel Tier-4 Heavy Unit</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block" />
            <span className="text-slate-200">EV Heavy High-Voltage Unit</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block animate-pulse" />
            <span className="text-rose-300 font-bold">Active Safety Infraction</span>
          </div>
        </div>
      </div>
    </div>
  );
};
