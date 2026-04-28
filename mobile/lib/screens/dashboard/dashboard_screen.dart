import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
      setState(() { _plan = active.isNotEmpty ? active.first : (plans.isNotEmpty ? plans.first : null); });
    } catch (e) {
      setState(() => _error = 'Kon trainingsplan niet laden');
    } finally {
      setState(() => _loading = false);
    }
  }

  List<WorkoutSession> get _thisWeekSessions {
    if (_plan == null) return [];
    final now = DateTime.now();
    return _plan!.sessions.where((s) {
      if (s.scheduledDate == null) return false;
      final d = s.scheduledDate!;
      final weekStart = now.subtract(Duration(days: now.weekday - 1));
      final weekEnd = weekStart.add(const Duration(days: 6));
      return !d.isBefore(weekStart) && !d.isAfter(weekEnd);
    }).toList()
      ..sort((a, b) => a.scheduledDate!.compareTo(b.scheduledDate!));
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
                          const SizedBox(height: 20),
                          if (_nextSession != null) ...[
                            _buildSectionHeader('Volgende training'),
                            const SizedBox(height: 8),
                            SessionCard(
                              session: _nextSession!,
                              onTap: () => context.go('/plan'),
                            ),
                            const SizedBox(height: 20),
                          ],
                          _buildSectionHeader('Deze week'),
                          const SizedBox(height: 8),
                          if (_thisWeekSessions.isEmpty)
                            const _EmptyWeek()
                          else
                            ...(_thisWeekSessions.map((s) => Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: SessionCard(
                                    session: s,
                                    onTap: () => context.go('/plan'),
                                  ),
                                ))),
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
