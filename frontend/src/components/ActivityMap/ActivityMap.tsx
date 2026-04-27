"use client";

import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { ActivityGpsPoint } from "@/types";

function FitBounds({ points }: { points: ActivityGpsPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) {
      const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number]));
      map.fitBounds(bounds, { padding: [24, 24] });
    }
  }, [map, points]);
  return null;
}

interface Props {
  track: ActivityGpsPoint[];
  className?: string;
}

export function ActivityMap({ track, className = "h-64 lg:h-96" }: Props) {
  if (track.length === 0) {
    return (
      <div className={`${className} w-full rounded-2xl bg-slate-800/50 border border-slate-700/40 flex items-center justify-center`}>
        <p className="text-sm text-slate-500">Geen GPS-data beschikbaar</p>
      </div>
    );
  }

  const center: [number, number] = [track[0].lat, track[0].lon];
  const positions = track.map((p) => [p.lat, p.lon] as [number, number]);

  return (
    <MapContainer
      center={center}
      zoom={13}
      scrollWheelZoom={false}
      className={`${className} w-full rounded-2xl z-0`}
      style={{ background: "#e5e3df" }}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
      />
      <Polyline positions={positions} color="#22c55e" weight={3} opacity={0.9} />
      <FitBounds points={track} />
    </MapContainer>
  );
}
