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
                ? const Center(child: Text('Kon activiteit niet laden',
                    style: TextStyle(color: Colors.red)))
                : _buildBody(),
      );

  Widget _buildBody() {
    final d = _detail!;
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
                  title: 'Tempo',
                  color: const Color(0xFF22c55e),
                  spots: _buildSpots(d.streams.time, d.streams.pace),
                  formatY: (v) => _fmtPace(v),
                  reversed: true,
                  yInterval: _niceInterval(_buildSpots(d.streams.time, d.streams.pace), [5, 10, 15, 30, 60, 120]),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasHeartRate) ...[
                _ChartCard(
                  title: 'Hartslag',
                  color: const Color(0xFFef4444),
                  spots: _buildSpots(d.streams.time,
                      d.streams.heartRate.map((v) => v?.toDouble()).toList()),
                  formatY: (v) => '${v.round()} bpm',
                  yInterval: _niceInterval(
                    _buildSpots(d.streams.time, d.streams.heartRate.map((v) => v?.toDouble()).toList()),
                    [5, 10, 20, 25],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasCadence) ...[
                _ChartCard(
                  title: 'Cadans',
                  color: const Color(0xFF8b5cf6),
                  spots: _buildSpots(d.streams.time,
                      d.streams.cadence.map((v) => v?.toDouble()).toList()),
                  formatY: (v) => '${v.round()} spm',
                  yInterval: _niceInterval(
                    _buildSpots(d.streams.time, d.streams.cadence.map((v) => v?.toDouble()).toList()),
                    [2, 5, 10, 20],
                  ),
                ),
                const SizedBox(height: 12),
              ],
              if (d.streams.hasAltitude) ...[
                _ChartCard(
                  title: 'Hoogte',
                  color: const Color(0xFFf59e0b),
                  spots: _buildSpots(d.streams.time, d.streams.altitude),
                  formatY: (v) => '${v.round()} m',
                  filled: true,
                  yInterval: _niceInterval(
                    _buildSpots(d.streams.time, d.streams.altitude),
                    [5, 10, 25, 50, 100],
                  ),
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
                    border: Border.all(color: const Color(0xFF6366f1).withOpacity(0.3)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.psychology, color: Color(0xFF6366f1), size: 18),
                          SizedBox(width: 8),
                          Text('Wetenschappelijke analyse',
                              style: TextStyle(
                                  color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(d.aiFeedback!,
                          style: const TextStyle(
                              color: Color(0xFFcbd5e1), fontSize: 13, height: 1.6)),
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
          initialCameraFit: CameraFit.bounds(bounds: bounds, padding: const EdgeInsets.all(24)),
          interactionOptions: const InteractionOptions(flags: InteractiveFlag.none),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'nl.ultimaterunning.app',
          ),
          PolylineLayer(
            polylines: [
              Polyline(points: points, strokeWidth: 3, color: const Color(0xFF6366f1)),
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
        _StatTile(icon: Icons.route, label: 'Afstand', value: '${s.distanceKm.toStringAsFixed(2)} km'),
        _StatTile(icon: Icons.timer, label: 'Duur', value: s.durationSeconds != null ? _fmtTime(s.durationSeconds!) : '–'),
        _StatTile(icon: Icons.speed, label: 'Tempo', value: s.avgPacePerKm != null ? '${s.avgPacePerKm} /km' : '–'),
        if (s.avgHeartRate != null)
          _StatTile(icon: Icons.favorite, label: 'Hartslag', value: '${s.avgHeartRate} bpm',
              sub: s.maxHeartRate != null ? 'max ${s.maxHeartRate}' : null),
        if (s.avgCadence != null)
          _StatTile(icon: Icons.swap_vert, label: 'Cadans', value: '${s.avgCadence} spm'),
        if (s.elevationGainM != null)
          _StatTile(icon: Icons.trending_up, label: 'Stijging', value: '${s.elevationGainM!.round()} m'),
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
    // range too small for any candidate → use smallest so at least 1–2 labels appear
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

class _StatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String? sub;
  const _StatTile({required this.icon, required this.label, required this.value, this.sub});

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
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                maxLines: 1, overflow: TextOverflow.ellipsis),
            Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 10)),
            if (sub != null)
              Text(sub!, style: const TextStyle(color: Color(0xFF64748b), fontSize: 10)),
          ],
        ),
      );
}

class _ChartCard extends StatelessWidget {
  final String title;
  final Color color;
  final List<FlSpot> spots;
  final String Function(double) formatY;
  final bool reversed;
  final bool filled;
  final double? yInterval;

  const _ChartCard({
    required this.title,
    required this.color,
    required this.spots,
    required this.formatY,
    this.reversed = false,
    this.filled = false,
    this.yInterval,
  });

  @override
  Widget build(BuildContext context) {
    if (spots.isEmpty) return const SizedBox.shrink();
    final minY = spots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final range = (maxY - minY).clamp(1.0, double.infinity);
    final padded = range * 0.1;

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 14, 12, 8),
      decoration: BoxDecoration(
        color: const Color(0xFF1e293b),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13)),
          const SizedBox(height: 10),
          SizedBox(
            height: 120,
            child: LineChart(
              LineChartData(
                minY: reversed ? maxY + padded : minY - padded,
                maxY: reversed ? minY - padded : maxY + padded,
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (_) => FlLine(
                    color: const Color(0xFF334155),
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 44,
                      interval: reversed && yInterval != null ? -yInterval! : yInterval,
                      getTitlesWidget: (v, meta) {
                        if (v == meta.min || v == meta.max) return const SizedBox.shrink();
                        return Text(
                          formatY(v),
                          style: const TextStyle(color: Color(0xFF64748b), fontSize: 9),
                        );
                      },
                    ),
                  ),
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipColor: (_) => const Color(0xFF0f172a),
                    getTooltipItems: (spots) => spots.map((s) => LineTooltipItem(
                          formatY(s.y),
                          TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12),
                        )).toList(),
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    curveSmoothness: 0.3,
                    color: color,
                    barWidth: 2,
                    dotData: const FlDotData(show: false),
                    belowBarData: filled
                        ? BarAreaData(
                            show: true,
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [color.withOpacity(0.3), color.withOpacity(0)],
                            ),
                          )
                        : BarAreaData(show: false),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
