import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../models/activity.dart';
import '../../services/api_service.dart';

class AnalyseScreen extends StatefulWidget {
  const AnalyseScreen({super.key});
  @override
  State<AnalyseScreen> createState() => _AnalyseScreenState();
}

class _AnalyseScreenState extends State<AnalyseScreen> {
  final _api = ApiService();
  List<ActivitySummary> _activities = [];
  bool _loading = true;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await _api.getActivities();
      final list = res.data as List? ?? [];
      setState(() {
        _activities = list.map((a) => ActivitySummary.fromJson(a)).toList();
        _activities.sort((a, b) => b.startTime.compareTo(a.startTime));
      });
    } catch (_) {
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _sync() async {
    setState(() => _syncing = true);
    try {
      await _api.syncGarmin();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Sync mislukt. Controleer je Garmin-koppeling.')),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Analyse'),
          actions: [
            if (_syncing)
              const Padding(
                padding: EdgeInsets.all(14),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              )
            else
              IconButton(
                icon: const Icon(Icons.sync),
                tooltip: 'Garmin sync',
                onPressed: _sync,
              ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _activities.isEmpty
                ? _buildEmpty()
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _activities.length,
                      itemBuilder: (_, i) => _ActivityTile(
                        activity: _activities[i],
                        onTap: () => context.go('/analyse/${_activities[i].activityId}'),
                      ),
                    ),
                  ),
      );

  Widget _buildEmpty() => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.bar_chart, size: 64, color: Color(0xFF334155)),
            const SizedBox(height: 16),
            const Text('Geen activiteiten gevonden',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('Sync je Garmin om activiteiten te laden',
                style: TextStyle(color: Colors.grey[500])),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _sync,
              icon: const Icon(Icons.sync),
              label: const Text('Garmin synchroniseren'),
            ),
          ],
        ),
      );
}

class _ActivityTile extends StatelessWidget {
  final ActivitySummary activity;
  final VoidCallback onTap;

  const _ActivityTile({required this.activity, required this.onTap});

  String _fmtDuration(int secs) {
    final h = secs ~/ 3600;
    final m = (secs % 3600) ~/ 60;
    final s = secs % 60;
    if (h > 0) return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  String _fmtDate(String iso) {
    try {
      final dt = DateTime.parse(iso.replaceFirst(' ', 'T')).toLocal();
      return DateFormat('EEE d MMM, HH:mm', 'nl').format(dt);
    } catch (_) {
      return iso.length > 10 ? iso.substring(0, 10) : iso;
    }
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF1e293b),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: const Color(0xFF6366f1).withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.directions_run, color: Color(0xFF6366f1), size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(activity.name.isNotEmpty ? activity.name : 'Hardlooptraining',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
                        maxLines: 1, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 2),
                    Text(_fmtDate(activity.startTime),
                        style: const TextStyle(color: Color(0xFF64748b), fontSize: 12)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _Chip(Icons.route, '${activity.distanceKm.toStringAsFixed(1)} km'),
                        if (activity.durationSeconds != null) ...[
                          const SizedBox(width: 8),
                          _Chip(Icons.timer, _fmtDuration(activity.durationSeconds!)),
                        ],
                        if (activity.avgPacePerKm != null) ...[
                          const SizedBox(width: 8),
                          _Chip(Icons.speed, '${activity.avgPacePerKm} /km'),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Color(0xFF334155)),
            ],
          ),
        ),
      );
}

class _Chip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _Chip(this.icon, this.label);

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: const Color(0xFF64748b)),
          const SizedBox(width: 3),
          Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
        ],
      );
}
