"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Maximize2, X, Heart, Activity, Ruler, Clock, TrendingUp, Zap } from "lucide-react";
import { useState } from "react";
import dynamic from "next/dynamic";
import { Link } from "@/i18n/navigation";
import { garminApi } from "@/lib/api";
import { ActivityDetail } from "@/types";
import { Navbar } from "@/components/ui/Navbar";
import { Brain } from "lucide-react";
import {
  ResponsiveContainer, ComposedChart, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip,
} from "recharts";

const ActivityMap = dynamic(
  () => import("@/components/ActivityMap/ActivityMap").then((m) => m.ActivityMap),
  { ssr: false, loading: () => <div className="h-64 lg:h-96 w-full rounded-2xl bg-slate-800/50 animate-pulse" /> }
);

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmtTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function fmtPace(secPerKm: number): string {
  const m = Math.floor(secPerKm / 60);
  const s = Math.round(secPerKm % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function buildChartData(streams: ActivityDetail["streams"]) {
  const { time, pace, heart_rate, cadence, altitude } = streams;
  const n = time.length;
  return Array.from({ length: n }, (_, i) => ({
    t: time[i],
    pace: pace[i] ?? null,
    hr: heart_rate[i] ?? null,
    cad: cadence[i] ?? null,
    alt: altitude[i] ?? null,
  }));
}

// ── Stat card ──────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="card flex flex-col gap-1 min-w-0">
      <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium">
        {icon}
        {label}
      </div>
      <p className="text-lg font-bold text-white leading-tight">{value}</p>
      {sub && <p className="text-[11px] text-slate-500">{sub}</p>}
    </div>
  );
}

// ── Chart config ───────────────────────────────────────────────────────────────

type ChartKey = "pace" | "altitude" | "heart_rate" | "cadence";

interface ChartConfig {
  key: ChartKey;
  label: string;
  dataKey: string;
  color: string;
  unit: string;
  reversed?: boolean;
  type: "line" | "area";
  tickFormatter?: (v: number) => string;
  tooltipFormatter?: (v: number) => string;
}

const CHART_CONFIGS: ChartConfig[] = [
  {
    key: "pace", label: "Tempo", dataKey: "pace", color: "#22c55e",
    unit: "/km", reversed: true, type: "line",
    tickFormatter: (v) => fmtPace(v),
    tooltipFormatter: (v) => `${fmtPace(v)} /km`,
  },
  {
    key: "altitude", label: "Hoogte", dataKey: "alt", color: "#f59e0b",
    unit: "m", type: "area",
    tickFormatter: (v) => `${Math.round(v)}m`,
    tooltipFormatter: (v) => `${Math.round(v)} m`,
  },
  {
    key: "heart_rate", label: "Hartslag", dataKey: "hr", color: "#ef4444",
    unit: "bpm", type: "line",
    tickFormatter: (v) => `${Math.round(v)}`,
    tooltipFormatter: (v) => `${Math.round(v)} bpm`,
  },
  {
    key: "cadence", label: "Cadans", dataKey: "cad", color: "#8b5cf6",
    unit: "spm", type: "line",
    tickFormatter: (v) => `${Math.round(v)}`,
    tooltipFormatter: (v) => `${Math.round(v)} spm`,
  },
];

// ── Combined chart ─────────────────────────────────────────────────────────────

function CombinedChartInner({
  primary, secondary, data, height,
}: {
  primary: ChartConfig;
  secondary?: ChartConfig;
  data: ReturnType<typeof buildChartData>;
  height: number | `${number}%`;
}) {
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-slate-800 border border-slate-700/60 rounded-xl px-3 py-2 text-xs shadow-xl space-y-0.5">
        <p className="text-slate-400 text-[10px]">{fmtTime(label)}</p>
        {payload.map((entry: any, i: number) => {
          const cfg = CHART_CONFIGS.find((c) => c.dataKey === entry.dataKey);
          const val = entry.value;
          if (val == null) return null;
          return (
            <p key={i} className="font-semibold" style={{ color: cfg?.color || entry.color }}>
              {cfg?.tooltipFormatter ? cfg.tooltipFormatter(val) : `${val} ${cfg?.unit ?? ""}`}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 4, right: secondary ? 42 : 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${primary.key}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={primary.color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={primary.color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey="t"
          tickFormatter={fmtTime}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          minTickGap={60}
        />
        <YAxis
          yAxisId="left"
          domain={["auto", "auto"]}
          reversed={primary.reversed}
          tickFormatter={primary.tickFormatter}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          width={38}
        />
        {secondary && (
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={["auto", "auto"]}
            reversed={secondary.reversed}
            tickFormatter={secondary.tickFormatter}
            tick={{ fill: secondary.color + "cc", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={38}
          />
        )}
        <Tooltip content={<CustomTooltip />} position={{ y: 0 }} />

        {/* Primary series */}
        {primary.type === "area" ? (
          <Area
            yAxisId="left"
            type="monotone"
            dataKey={primary.dataKey}
            stroke={primary.color}
            fill={`url(#grad-${primary.key})`}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        ) : (
          <Line
            yAxisId="left"
            type="monotone"
            dataKey={primary.dataKey}
            stroke={primary.color}
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        )}

        {/* Secondary overlay — dashed line, own Y-axis */}
        {secondary && (
          <Line
            yAxisId="right"
            type="monotone"
            dataKey={secondary.dataKey}
            stroke={secondary.color}
            strokeWidth={1.5}
            strokeDasharray="5 3"
            strokeOpacity={0.85}
            dot={false}
            connectNulls
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// ── Chart card ─────────────────────────────────────────────────────────────────

function ChartCard({
  config, data, onFullscreen,
}: {
  config: ChartConfig;
  data: ReturnType<typeof buildChartData>;
  onFullscreen: (overlay: ChartKey | null) => void;
}) {
  const [overlay, setOverlay] = useState<ChartKey | null>(null);

  const hasData = data.some((d) => d[config.dataKey as keyof typeof d] !== null);
  if (!hasData) return null;

  const others = CHART_CONFIGS.filter(
    (c) => c.key !== config.key && data.some((d) => d[c.dataKey as keyof typeof d] !== null)
  );
  const secondaryConfig = overlay ? CHART_CONFIGS.find((c) => c.key === overlay) : undefined;

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-sm font-semibold text-white shrink-0">{config.label}</p>
        <div className="flex items-center gap-1.5 flex-wrap">
          {others.map((oc) => (
            <button
              key={oc.key}
              onClick={() => setOverlay(overlay === oc.key ? null : oc.key)}
              className="text-[10px] px-2 py-0.5 rounded-full border transition-all"
              style={
                overlay === oc.key
                  ? { backgroundColor: oc.color + "22", borderColor: oc.color, color: oc.color }
                  : { borderColor: "#334155", color: "#64748b" }
              }
            >
              {oc.label}
            </button>
          ))}
          <button
            onClick={() => onFullscreen(overlay)}
            className="text-slate-500 hover:text-slate-300 transition-colors p-1 rounded-lg hover:bg-surface-elevated"
            title="Volledig scherm"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <CombinedChartInner primary={config} secondary={secondaryConfig} data={data} height={160} />
    </div>
  );
}

// ── Fullscreen modal ───────────────────────────────────────────────────────────

function FullscreenChart({
  config, initialOverlay, data, onClose,
}: {
  config: ChartConfig;
  initialOverlay: ChartKey | null;
  data: ReturnType<typeof buildChartData>;
  onClose: () => void;
}) {
  const [overlay, setOverlay] = useState<ChartKey | null>(initialOverlay);

  const others = CHART_CONFIGS.filter(
    (c) => c.key !== config.key && data.some((d) => d[c.dataKey as keyof typeof d] !== null)
  );
  const secondaryConfig = overlay ? CHART_CONFIGS.find((c) => c.key === overlay) : undefined;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ duration: 0.2 }}
        className="flex-1 flex flex-col p-4 lg:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            <p className="text-lg font-bold text-white">{config.label}</p>
            <div className="flex items-center gap-1.5 flex-wrap">
              {others.map((oc) => (
                <button
                  key={oc.key}
                  onClick={() => setOverlay(overlay === oc.key ? null : oc.key)}
                  className="text-[11px] px-2.5 py-1 rounded-full border transition-all"
                  style={
                    overlay === oc.key
                      ? { backgroundColor: oc.color + "22", borderColor: oc.color, color: oc.color }
                      : { borderColor: "#334155", color: "#64748b" }
                  }
                >
                  {oc.label}
                </button>
              ))}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-2 rounded-xl hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0">
          <CombinedChartInner primary={config} secondary={secondaryConfig} data={data} height={"100%" as `${number}%`} />
        </div>
      </motion.div>
    </motion.div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function ActivityDetailPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const t = useTranslations("analyse");
  const [fullscreen, setFullscreen] = useState<{ key: ChartKey; overlay: ChartKey | null } | null>(null);

  const { data, isLoading, error } = useQuery<ActivityDetail>({
    queryKey: ["activity", activityId],
    queryFn: () => garminApi.getActivity(activityId).then((r) => r.data),
    staleTime: 10 * 60 * 1000,
  });

  const chartData = data ? buildChartData(data.streams) : [];

  return (
    <>
      <div className="min-h-screen lg:pl-60">
        <Navbar />
        <main className="px-4 py-6 pb-24 lg:pb-6 max-w-5xl mx-auto space-y-5">
          {/* Header */}
          <div className="flex items-center gap-3">
            <Link href="/analyse" className="btn-ghost px-2 py-2">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-white truncate">
                {data?.summary.name || t("loading")}
              </h1>
              {data?.summary.start_time && (
                <p className="text-xs text-slate-400">{data.summary.start_time.replace("T", " ").slice(0, 16)}</p>
              )}
            </div>
          </div>

          {isLoading && (
            <div className="flex justify-center py-20">
              <span className="w-8 h-8 rounded-full border-2 border-brand-500 border-t-transparent animate-spin" />
            </div>
          )}

          {error && (
            <div className="card text-center py-10 text-red-400 text-sm">
              {t("error")}
            </div>
          )}

          {data && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
              {/* Map */}
              <ActivityMap track={data.gps_track} className="h-64 lg:h-96" />

              {/* Stats grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <StatCard
                  icon={<Ruler className="w-3.5 h-3.5" />}
                  label={t("stats.distance")}
                  value={`${data.summary.distance_km} km`}
                />
                <StatCard
                  icon={<Clock className="w-3.5 h-3.5" />}
                  label={t("stats.duration")}
                  value={fmtTime(data.summary.duration_seconds)}
                />
                <StatCard
                  icon={<Zap className="w-3.5 h-3.5" />}
                  label={t("stats.pace")}
                  value={data.summary.avg_pace_per_km ? `${data.summary.avg_pace_per_km} /km` : "–"}
                />
                <StatCard
                  icon={<Heart className="w-3.5 h-3.5" />}
                  label={t("stats.heartRate")}
                  value={data.summary.avg_heart_rate ? `${data.summary.avg_heart_rate} bpm` : "–"}
                  sub={data.summary.max_heart_rate ? `max ${data.summary.max_heart_rate}` : undefined}
                />
                <StatCard
                  icon={<Activity className="w-3.5 h-3.5" />}
                  label={t("stats.cadence")}
                  value={data.summary.avg_cadence ? `${data.summary.avg_cadence} spm` : "–"}
                />
                <StatCard
                  icon={<TrendingUp className="w-3.5 h-3.5" />}
                  label={t("stats.elevation")}
                  value={data.summary.elevation_gain_m ? `${Math.round(data.summary.elevation_gain_m)} m` : "–"}
                />
              </div>

              {/* Charts grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {CHART_CONFIGS.map((cfg) => (
                  <ChartCard
                    key={cfg.key}
                    config={cfg}
                    data={chartData}
                    onFullscreen={(overlay) => setFullscreen({ key: cfg.key, overlay })}
                  />
                ))}
              </div>

              {/* AI feedback (Elite tier) */}
              {data.ai_feedback && (
                <div className="card space-y-3">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-brand-400" />
                    <p className="text-sm font-semibold text-white">Wetenschappelijke analyse</p>
                  </div>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                    {data.ai_feedback}
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </main>
      </div>

      {/* Fullscreen modal */}
      <AnimatePresence>
        {fullscreen && data && (() => {
          const cfg = CHART_CONFIGS.find((c) => c.key === fullscreen.key)!;
          return (
            <FullscreenChart
              key={fullscreen.key}
              config={cfg}
              initialOverlay={fullscreen.overlay}
              data={chartData}
              onClose={() => setFullscreen(null)}
            />
          );
        })()}
      </AnimatePresence>
    </>
  );
}
