import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../models/activity.dart';
import '../../services/api_service.dart';

class ActivityDetailScreen extends StatefulWidget {
  final String activityId;
  final int? friendId;
  const ActivityDetailScreen({super.key, required this.activityId, this.friendId});

  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

// ---------------------------------------------------------------------------
// Data class holding one chart series.
// ---------------------------------------------------------------------------
class _Series {
  final String key;
  final String label;
  final Color color;
  final List<FlSpot> spots;
  final String Function(double) formatY;
  final bool reversed;
  final bool filled;
  final double? yInterval;

  _Series({
    required this.key,
    required this.label,
    required this.color,
    required this.spots,
    required this.formatY,
    this.reversed = false,
    this.filled = false,
    this.yInterval,
  });
}

// ---------------------------------------------------------------------------
// Screen state
// ---------------------------------------------------------------------------
class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  final _api = ApiService();
  ActivityDetail? _detail;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = widget.friendId != null
          ? await _api.getFriendActivity(widget.friendId!, widget.activityId)
          : await _api.getActivity(widget.activityId);
      setState(() => _detail = ActivityDetail.fromJson(res.data));
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _fmtTime(int secs) {
    final h = secs ~/ 3600;
    final m = (secs % 3600) ~/ 60;
    final s = secs % 60;
    if (h > 0) return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_detail?.summary.name.isNotEmpty == true
              ? _detail!.summary.name
              : 'Activiteit'),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _detail == null
                ? const Center(
                    child: Text('Kon activiteit niet laden',
                        style: TextStyle(color: Colors.red)))
                : _buildBody(),
      );

  Widget _buildBody() {
    final d = _detail!;

    // Build all four series (empty spots when stream unavailable).
    final paceSpots = d.streams.hasPace
        ? _buildSpots(d.streams.time, d.streams.pace)
        : <FlSpot>[];
    final hrSpots = d.streams.hasHeartRate
        ? _buildSpots(
            d.streams.time,
            d.streams.heartRate.map((v) => v?.toDouble()).toList())
        : <FlSpot>[];
    final cadSpots = d.streams.hasCadence
        ? _buildSpots(
            d.streams.time,
            d.streams.cadence.map((v) => v?.toDouble()).toList())
        : <FlSpot>[];
    final altSpots = d.streams.hasAltitude
        ? _buildSpots(d.streams.time, d.streams.altitude)
        : <FlSpot>[];

    final paceSeries = _Series(
      key: 'pace',
      label: 'Tempo',
      color: const Color(0xFF22c55e),
      spots: paceSpots,
      formatY: _fmtPace,
      reversed: true,
      yInterval: _niceInterval(paceSpots, [5, 10, 15, 30, 60, 120]),
    );
    final hrSeries = _Series(
      key: 'hr',
      label: 'Hartslag',
      color: const Color(0xFFef4444),
      spots: hrSpots,
      formatY: (v) => '${v.round()} bpm',
      yInterval: _niceInterval(hrSpots, [5, 10, 20, 25]),
    );
    final cadSeries = _Series(
      key: 'cad',
      label: 'Cadans',
      color: const Color(0xFF8b5cf6),
      spots: cadSpots,
      formatY: (v) => '${v.round()} spm',
      yInterval: _niceInterval(cadSpots, [2, 5, 10, 20]),
    );
    final altSeries = _Series(
      key: 'alt',
      label: 'Hoogte',
      color: const Color(0xFFf59e0b),
      spots: altSpots,
      formatY: (v) => '${v.round()} m',
      filled: true,
      yInterval: _niceInterval(altSpots, [5, 10, 25, 50, 100]),
    );

    final allSeries = [paceSeries, hrSeries, cadSeries, altSeries];

    // Helper: build the others list for a given primary key.
    List<_Series> othersFor(_Series primary) => allSeries
        .where((s) => s.key != primary.key && s.spots.isNotEmpty)
        .toList();

    return ListView(
      children: [
        // Map
        if (d.gpsTrack.isNotEmpty) _buildMap(d.gpsTrack),

        // Stats
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildStatGrid(d.summary),
              const SizedBox(height: 20),

              // Charts
              if (d.streams.hasPace) ...[
                _ChartCard(
                  primary: paceSeries,
                  others: othersFor(paceSeries),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasHeartRate) ...[
                _ChartCard(
                  primary: hrSeries,
                  others: othersFor(hrSeries),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasCadence) ...[
                _ChartCard(
                  primary: cadSeries,
                  others: othersFor(cadSeries),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasAltitude) ...[
                _ChartCard(
                  primary: altSeries,
                  others: othersFor(altSeries),
                ),
                const SizedBox(height: 12),
              ],

              // AI feedback
              if (d.aiFeedback != null) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1e293b),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: const Color(0xFF6366f1).withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.psychology,
                              color: Color(0xFF6366f1), size: 18),
                          SizedBox(width: 8),
                          Text('Wetenschappelijke analyse',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(d.aiFeedback!,
                          style: const TextStyle(
                              color: Color(0xFFcbd5e1),
                              fontSize: 13,
                              height: 1.6)),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 24),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMap(List<GpsPoint> track) {
    final points = track.map((p) => LatLng(p.lat, p.lon)).toList();
    final bounds = LatLngBounds.fromPoints(points);
    return SizedBox(
      height: 220,
      child: FlutterMap(
        options: MapOptions(
          initialCameraFit: CameraFit.bounds(
              bounds: bounds, padding: const EdgeInsets.all(24)),
          interactionOptions: const InteractionOptions(
              flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'nl.ultimaterunning.app',
          ),
          PolylineLayer(
            polylines: [
              Polyline(
                  points: points,
                  strokeWidth: 3,
                  color: const Color(0xFF6366f1)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatGrid(ActivitySummary s) {
    return GridView.count(
      crossAxisCount: 3,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.4,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      children: [
        _StatTile(
            icon: Icons.route,
            label: 'Afstand',
            value: '${s.distanceKm.toStringAsFixed(2)} km'),
        _StatTile(
            icon: Icons.timer,
            label: 'Duur',
            value: s.durationSeconds != null
                ? _fmtTime(s.durationSeconds!)
                : '–'),
        _StatTile(
            icon: Icons.speed,
            label: 'Tempo',
            value:
                s.avgPacePerKm != null ? '${s.avgPacePerKm} /km' : '–'),
        if (s.avgHeartRate != null)
          _StatTile(
              icon: Icons.favorite,
              label: 'Hartslag',
              value: '${s.avgHeartRate} bpm',
              sub: s.maxHeartRate != null ? 'max ${s.maxHeartRate}' : null),
        if (s.avgCadence != null)
          _StatTile(
              icon: Icons.swap_vert,
              label: 'Cadans',
              value: '${s.avgCadence} spm'),
        if (s.elevationGainM != null)
          _StatTile(
              icon: Icons.trending_up,
              label: 'Stijging',
              value: '${s.elevationGainM!.round()} m'),
      ],
    );
  }

  double? _niceInterval(List<FlSpot> spots, List<int> candidates) {
    if (spots.isEmpty) return null;
    final minY = spots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final range = maxY - minY;
    for (final step in candidates) {
      final ticks = range / step;
      if (ticks >= 2 && ticks <= 6) return step.toDouble();
    }
    if (range < candidates.first * 2) return candidates.first.toDouble();
    return candidates.last.toDouble();
  }

  List<FlSpot> _buildSpots(List<int> time, List<double?> values) {
    final spots = <FlSpot>[];
    final step = (time.length / 300).ceil().clamp(1, 999);
    for (int i = 0; i < time.length; i += step) {
      final v = values.length > i ? values[i] : null;
      if (v != null) spots.add(FlSpot(time[i].toDouble(), v));
    }
    return spots;
  }

  String _fmtPace(double secPerKm) {
    final m = secPerKm ~/ 60;
    final s = (secPerKm % 60).round();
    return '$m:${s.toString().padLeft(2, '0')}';
  }
}

// ---------------------------------------------------------------------------
// _StatTile
// ---------------------------------------------------------------------------
class _StatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String? sub;
  const _StatTile(
      {required this.icon, required this.label, required this.value, this.sub});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFF1e293b),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 16, color: const Color(0xFF6366f1)),
            const SizedBox(height: 4),
            Text(value,
                style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13),
                maxLines: 1,
                overflow: TextOverflow.ellipsis),
            Text(label,
                style:
                    const TextStyle(color: Color(0xFF64748b), fontSize: 10)),
            if (sub != null)
              Text(sub!,
                  style: const TextStyle(
                      color: Color(0xFF64748b), fontSize: 10)),
          ],
        ),
      );
}

// ---------------------------------------------------------------------------
// _ChartCard  – StatefulWidget with optional overlay series
// ---------------------------------------------------------------------------
class _ChartCard extends StatefulWidget {
  final _Series primary;
  final List<_Series> others;

  const _ChartCard({required this.primary, required this.others});

  @override
  State<_ChartCard> createState() => _ChartCardState();
}

class _ChartCardState extends State<_ChartCard> {
  String? _overlayKey;

  _Series get primary => widget.primary;

  _Series? get _overlayOrNull => _overlayKey == null
      ? null
      : widget.others.where((s) => s.key == _overlayKey).firstOrNull;

  @override
  Widget build(BuildContext context) {
    if (primary.spots.isEmpty) return const SizedBox.shrink();

    // Primary chart spots — negate Y for reversed axes so fl_chart sorts ascending.
    final chartSpots = primary.reversed
        ? primary.spots.map((s) => FlSpot(s.x, -s.y)).toList()
        : primary.spots;

    final minY =
        chartSpots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
    final maxY =
        chartSpots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final range = (maxY - minY).clamp(1.0, double.infinity);
    final padded = range * 0.1;

    double labelY(double v) => primary.reversed ? -v : v;

    // Build overlay bar if an overlay is selected.
    final overlay = _overlayOrNull;
    LineChartBarData? overlayBar;
    List<FlSpot> overlayNormSpots = [];

    if (overlay != null && overlay.spots.isNotEmpty) {
      // Raw overlay spots (possibly negated for reversed overlay).
      final rawOverlaySpots = overlay.reversed
          ? overlay.spots.map((s) => FlSpot(s.x, -s.y)).toList()
          : overlay.spots;

      final sMin =
          rawOverlaySpots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
      final sMax =
          rawOverlaySpots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
      final sRange = (sMax - sMin).clamp(1.0, double.infinity);

      // Normalize secondary Y into primary Y range.
      overlayNormSpots = rawOverlaySpots
          .map((s) => FlSpot(
                s.x,
                (minY + padded) +
                    ((s.y - sMin) / sRange) * (range - 2 * padded),
              ))
          .toList();

      overlayBar = LineChartBarData(
        spots: overlayNormSpots,
        isCurved: true,
        curveSmoothness: 0.3,
        color: overlay.color,
        barWidth: 2,
        dotData: const FlDotData(show: false),
        dashArray: [6, 4],
        belowBarData: BarAreaData(show: false),
      );
    }

    // Assemble lineBarsData list.
    final bars = [
      LineChartBarData(
        spots: chartSpots,
        isCurved: true,
        curveSmoothness: 0.3,
        color: primary.color,
        barWidth: 2,
        dotData: const FlDotData(show: false),
        belowBarData: primary.filled
            ? BarAreaData(
                show: true,
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    primary.color.withOpacity(0.3),
                    primary.color.withOpacity(0),
                  ],
                ),
              )
            : BarAreaData(show: false),
      ),
      if (overlayBar != null) overlayBar,
    ];

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 14, 12, 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1e293b),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row: title + overlay chips
          Row(
            children: [
              Text(
                primary.label,
                style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13),
              ),
              const SizedBox(width: 8),
              // Overlay toggle chips for available other series
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: widget.others
                        .where((s) => s.spots.isNotEmpty)
                        .map((s) {
                      final active = _overlayKey == s.key;
                      return Padding(
                        padding: const EdgeInsets.only(right: 6),
                        child: GestureDetector(
                          onTap: () => setState(() =>
                              _overlayKey = active ? null : s.key),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: active
                                  ? s.color.withOpacity(0.2)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: active
                                    ? s.color
                                    : const Color(0xFF475569),
                                width: 1,
                              ),
                            ),
                            child: Text(
                              s.label,
                              style: TextStyle(
                                color: active
                                    ? s.color
                                    : const Color(0xFF94a3b8),
                                fontSize: 10,
                                fontWeight: active
                                    ? FontWeight.w600
                                    : FontWeight.normal,
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          SizedBox(
            height: 120,
            child: LineChart(
              LineChartData(
                minY: minY - padded,
                maxY: maxY + padded,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (_) => const FlLine(
                    color: Color(0xFF334155),
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 44,
                      interval: primary.yInterval,
                      getTitlesWidget: (v, meta) {
                        if (v == meta.min || v == meta.max) {
                          return const SizedBox.shrink();
                        }
                        return Text(
                          primary.formatY(labelY(v)),
                          style: const TextStyle(
                              color: Color(0xFF64748b), fontSize: 9),
                        );
                      },
                    ),
                  ),
                  rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false)),
                ),
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipColor: (_) => const Color(0xFF0f172a),
                    getTooltipItems: (touchedSpots) {
                      // Always show primary first, overlay second.
                      LineTooltipItem? primaryItem;
                      LineTooltipItem? overlayItem;
                      for (final s in touchedSpots) {
                        if (s.barIndex == 0) {
                          primaryItem = LineTooltipItem(
                            primary.formatY(labelY(s.y)),
                            TextStyle(color: primary.color, fontWeight: FontWeight.bold, fontSize: 12),
                          );
                        } else if (s.barIndex == 1 && overlay != null) {
                          final idx = s.spotIndex;
                          if (idx >= 0 && idx < overlay.spots.length) {
                            overlayItem = LineTooltipItem(
                              overlay.formatY(overlay.spots[idx].y),
                              TextStyle(color: overlay.color, fontWeight: FontWeight.bold, fontSize: 12),
                            );
                          }
                        }
                      }
                      final items = <LineTooltipItem?>[
                        if (primaryItem != null) primaryItem,
                        if (overlayItem != null) overlayItem,
                      ];
                      while (items.length < touchedSpots.length) items.add(null);
                      return items;
                    },
                  ),
                ),
                lineBarsData: bars,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
