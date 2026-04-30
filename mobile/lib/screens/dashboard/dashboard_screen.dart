import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../../models/plan.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';
import '../../widgets/session_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _api = ApiService();
  Plan? _plan;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final res = await _api.getPlans();
      final plans = (res.data as List).map((p) => Plan.fromJson(p)).toList();
      final active = plans.where((p) => p.status == 'active').toList();
      final base = active.isNotEmpty ? active.first : (plans.isNotEmpty ? plans.first : null);
      if (base != null) {
        final detail = await _api.getPlan(base.publicId);
        setState(() => _plan = Plan.fromJson(detail.data));
      } else {
        setState(() => _plan = null);
      }
    } catch (e) {
      setState(() => _error = 'Kon trainingsplan niet laden');
    } finally {
      setState(() => _loading = false);
    }
  }

  WorkoutSession? get _nextSession {
    final now = DateTime.now();
    final upcoming = _plan?.sessions.where((s) =>
        s.scheduledDate != null &&
        !s.isCompleted &&
        !s.scheduledDate!.isBefore(DateTime(now.year, now.month, now.day))).toList() ?? [];
    upcoming.sort((a, b) => a.scheduledDate!.compareTo(b.scheduledDate!));
    return upcoming.isNotEmpty ? upcoming.first : null;
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Hallo, ${user?.name.split(' ').first ?? 'Atleet'} 👋',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            if (_plan != null)
              Text(_plan!.title,
                  style: const TextStyle(fontSize: 12, color: Color(0xFF64748b))),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_error!, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 12),
                    ElevatedButton(onPressed: _load, child: const Text('Opnieuw')),
                  ],
                ))
              : _plan == null
                  ? _buildNoPlan()
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          _buildStats(),
                          const SizedBox(height: 16),
                          _buildPlanInfo(),
                          if (_plan!.paceZones != null && _plan!.paceZones!.isNotEmpty) ...[
                            const SizedBox(height: 16),
                            _buildPaceZones(),
                          ],
                          const SizedBox(height: 20),
                          _buildSectionHeader('Volgende training'),
                          const SizedBox(height: 8),
                          if (_nextSession != null)
                            SessionCard(
                              session: _nextSession!,
                              onTap: () => context.go('/plan'),
                            )
                          else
                            const _EmptyWeek(),
                        ],
                      ),
                    ),
    );
  }

  Widget _buildNoPlan() => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.directions_run, size: 64, color: Color(0xFF334155)),
            const SizedBox(height: 16),
            const Text('Geen trainingsplan gevonden',
                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('Maak een plan aan via de website',
                style: TextStyle(color: Colors.grey[500], fontSize: 14)),
          ],
        ),
      );

  Widget _buildStats() {
    final sessions = _plan!.sessions;
    final done = sessions.where((s) => s.isCompleted).length;
    final total = sessions.length;
    final progress = total > 0 ? done / total : 0.0;
    final weeklyKm = sessions
        .where((s) => s.isCompleted && s.distanceKm != null)
        .fold(0.0, (sum, s) => sum + s.distanceKm!);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Row(
              children: [
                _StatChip(icon: Icons.check_circle_outline, label: 'Voltooid', value: '$done/$total'),
                const SizedBox(width: 12),
                _StatChip(icon: Icons.route, label: 'KM (totaal)', value: '${weeklyKm.toStringAsFixed(0)} km'),
                const SizedBox(width: 12),
                _StatChip(icon: Icons.calendar_month, label: 'Weken', value: '${_plan!.weekCount}'),
              ],
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: const Color(0xFF334155),
              color: const Color(0xFF6366f1),
              borderRadius: BorderRadius.circular(4),
              minHeight: 6,
            ),
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerRight,
              child: Text('${(progress * 100).round()}% voltooid',
                  style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlanInfo() {
    final p = _plan!;
    final rows = <Widget>[];

    if (p.formattedGoal.isNotEmpty)
      rows.add(_InfoRow(Icons.flag_outlined, 'Doel', p.formattedGoal));
    if (p.formattedTargetTime.isNotEmpty)
      rows.add(_InfoRow(Icons.timer_outlined, 'Doeltijd', p.formattedTargetTime));
    if (p.targetPacePerKm != null)
      rows.add(_InfoRow(Icons.speed_outlined, 'Doeltempo', '${p.targetPacePerKm} /km'));
    if (p.weeklyKm != null)
      rows.add(_InfoRow(Icons.route_outlined, 'Km/week (huidig)', '${p.weeklyKm!.toStringAsFixed(0)} km'));
    if (p.raceDate != null)
      rows.add(_InfoRow(Icons.event_outlined, 'Wedstrijddatum',
          DateFormat('d MMM yyyy', 'nl').format(p.raceDate!)));
    if (p.startDate != null)
      rows.add(_InfoRow(Icons.play_circle_outline, 'Startdatum',
          DateFormat('d MMM yyyy', 'nl').format(p.startDate!)));

    if (rows.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Planinformatie',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 12),
            ...rows.map((r) => Padding(padding: const EdgeInsets.only(bottom: 8), child: r)),
          ],
        ),
      ),
    );
  }

  Widget _buildPaceZones() {
    const zoneLabels = {
      'easy': 'Rustig (easy)',
      'marathon': 'Marathon',
      'threshold': 'Drempel (tempo)',
      'interval': 'Interval',
      'repetition': 'Herhaling (rep)',
    };
    const zoneColors = {
      'easy': Color(0xFF22c55e),
      'marathon': Color(0xFF6366f1),
      'threshold': Color(0xFFf59e0b),
      'interval': Color(0xFFef4444),
      'repetition': Color(0xFFec4899),
    };

    final zones = _plan!.paceZones!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Trainingszones',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 12),
            ...zoneLabels.entries
                .where((e) => zones[e.key] != null)
                .map((e) {
                  final color = zoneColors[e.key] ?? const Color(0xFF64748b);
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(
                      children: [
                        Container(
                          width: 10, height: 10,
                          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(e.value,
                              style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
                        ),
                        Text('${zones[e.key]} /km',
                            style: TextStyle(
                                color: color, fontSize: 13, fontWeight: FontWeight.w600)),
                      ],
                    ),
                  );
                }),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) => Text(
        title,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
      );
}

class _StatChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _StatChip({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) => Expanded(
        child: Column(
          children: [
            Icon(icon, size: 20, color: const Color(0xFF6366f1)),
            const SizedBox(height: 4),
            Text(value,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
            Text(label,
                style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
          ],
        ),
      );
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _InfoRow(this.icon, this.label, this.value);

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 15, color: const Color(0xFF6366f1)),
          const SizedBox(width: 10),
          Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 13)),
          const Spacer(),
          Text(value,
              style: const TextStyle(
                  color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
        ],
      );
}

class _EmptyWeek extends StatelessWidget {
  const _EmptyWeek();
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: const Color(0xFF1e293b),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Center(
          child: Text('Geen trainingen gepland deze week',
              style: TextStyle(color: Colors.grey[500])),
        ),
      );
}
