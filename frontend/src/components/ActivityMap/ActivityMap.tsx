"use client";

import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { ActivityGpsPoint } from "@/types";
import { useTheme } from "@/components/ui/ThemeProvider";

// CARTO's basemaps are built on OpenStreetMap data, so both are credited.
const OSM_CREDIT = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
const CARTO_CREDIT = `${OSM_CREDIT}, &copy; <a href="https://carto.com/attributions">CARTO</a>`;

const CARTO_KEY = process.env.NEXT_PUBLIC_CARTO_API_KEY;

// CARTO has the dark basemap but needs a key — without one it stamps
// "API KEY Required" across every tile. OpenStreetMap needs none, so it stands
// in when the key is missing or rejected: the same tiles the Flutter app uses.
// A light map in dark mode beats an unreadable one.
const OSM_TILE = { url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: OSM_CREDIT };

const TILES = CARTO_KEY
  ? {
      dark: {
        url: `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`,
        bg: "#1e293b",
        attribution: CARTO_CREDIT,
      },
      light: {
        url: `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`,
        bg: "#e5e3df",
        attribution: CARTO_CREDIT,
      },
    }
  : {
      dark:  { ...OSM_TILE, bg: "#1e293b" },
      light: { ...OSM_TILE, bg: "#e5e3df" },
    };

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
  const { resolved } = useTheme();
  const tile = TILES[resolved];

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
      scrollWheelZoom={true}
      className={`${className} w-full rounded-2xl z-0`}
      style={{ background: tile.bg }}
    >
      <TileLayer
        key={resolved}
        url={tile.url}
        attribution={tile.attribution}
      />
      <Polyline positions={positions} color="#22c55e" weight={3} opacity={0.9} />
      <FitBounds points={track} />
    </MapContainer>
  );
}
