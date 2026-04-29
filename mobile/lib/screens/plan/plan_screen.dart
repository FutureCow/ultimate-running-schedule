import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../models/plan.dart';
import '../../services/api_service.dart';
import '../../widgets/session_card.dart';

class PlanScreen extends StatefulWidget {
  const PlanScreen({super.key});
  @override
  State<PlanScreen> createState() => _PlanScreenState();
}

class _PlanScreenState extends State<PlanScreen> {
  final _api = ApiService();
  Plan? _plan;
  bool _loading = true;
  String? _error;
  int _selectedWeek = 0;

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
      final plan = plans.isNotEmpty ? plans.first : null;
      if (plan != null) {
        final detail = await _api.getPlan(plan.publicId);
        final fullPlan = Plan.fromJson(detail.data);
        final currentWeek = _detectCurrentWeek(fullPlan);
        setState(() { _plan = fullPlan; _selectedWeek = currentWeek; });
      }
    } catch (e) {
      setState(() => _error = 'Kon plan niet laden: ${e.toString().split('\n').first}');
    } finally {
      setState(() => _loading = false);
    }
  }

  int _detectCurrentWeek(Plan plan) {
    final now = DateTime.now();
    for (final s in plan.sessions) {
      if (s.scheduledDate == null) continue;
      final d = s.scheduledDate!;
      final weekStart = now.subtract(Duration(days: now.weekday - 1));
      final weekEnd = weekStart.add(const Duration(days: 6));
      if (!d.isBefore(weekStart) && !d.isAfter(weekEnd)) return s.weekNumber;
    }
    return 1;
  }

  List<int> get _weeks {
    if (_plan == null) return [];
    return _plan!.sessions.map((s) => s.weekNumber).toSet().toList()..sort();
  }

  List<WorkoutSession> get _weekSessions {
    if (_plan == null) return [];
    return _plan!.sessions
        .where((s) => s.weekNumber == _selectedWeek)
        .toList()
      ..sort((a, b) => a.dayNumber.compareTo(b.dayNumber));
  }

  void _showSessionDetail(WorkoutSession session) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1e293b),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _SessionDetailSheet(session: session, onMarkComplete: _load),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_plan?.title ?? 'Trainingsplan'),
          actions: [
            IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
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
                ? const Center(child: Text('Geen trainingsplan gevonden',
                    style: TextStyle(color: Colors.white)))
                : Column(
                    children: [
                      _buildWeekSelector(),
                      Expanded(
                        child: RefreshIndicator(
                          onRefresh: _load,
                          child: ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              _buildWeekHeader(),
                              const SizedBox(height: 12),
                              ..._weekSessions.map((s) => Padding(
                                    padding: const EdgeInsets.only(bottom: 8),
                                    child: SessionCard(
                                      session: s,
                                      onTap: () => _showSessionDetail(s),
                                    ),
                                  )),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
      );

  Widget _buildWeekSelector() => SizedBox(
        height: 50,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          itemCount: _weeks.length,
          itemBuilder: (_, i) {
            final w = _weeks[i];
            final selected = w == _selectedWeek;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: GestureDetector(
                onTap: () => setState(() => _selectedWeek = w),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  decoration: BoxDecoration(
                    color: selected ? const Color(0xFF6366f1) : const Color(0xFF1e293b),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: selected ? const Color(0xFF6366f1) : const Color(0xFF334155),
                    ),
                  ),
                  child: Text('Week $w',
                      style: TextStyle(
                        color: selected ? Colors.white : const Color(0xFF64748b),
                        fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                        fontSize: 13,
                      )),
                ),
              ),
            );
          },
        ),
      );

  Widget _buildWeekHeader() {
    final sessions = _weekSessions;
    final done = sessions.where((s) => s.isCompleted).length;
    final totalKm = sessions
        .where((s) => s.distanceKm != null)
        .fold(0.0, (sum, s) => sum + s.distanceKm!);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1e293b),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Expanded(child: _WeekStat(label: 'Trainingen', value: '${sessions.length}')),
          Expanded(child: _WeekStat(label: 'Voltooid', value: '$done/${sessions.length}')),
          Expanded(child: _WeekStat(label: 'Afstand', value: '${totalKm.toStringAsFixed(0)} km')),
        ],
      ),
    );
  }
}

class _WeekStat extends StatelessWidget {
  final String label;
  final String value;
  const _WeekStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Text(value,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
          Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
        ],
      );
}

class _SessionDetailSheet extends StatefulWidget {
  final WorkoutSession session;
  final VoidCallback onMarkComplete;
  const _SessionDetailSheet({required this.session, required this.onMarkComplete});

  @override
  State<_SessionDetailSheet> createState() => _SessionDetailSheetState();
}

class _SessionDetailSheetState extends State<_SessionDetailSheet> {
  final _api = ApiService();
  bool _marking = false;

  static const _typeColors = {
    'easy': Color(0xFF22c55e), 'easy_run': Color(0xFF22c55e), 'recovery': Color(0xFF22c55e),
    'tempo': Color(0xFFf59e0b),
    'interval': Color(0xFFef4444),
    'long': Color(0xFF6366f1), 'long_run': Color(0xFF6366f1),
    'rest': Color(0xFF64748b),
    'race': Color(0xFFec4899),
    'strength': Color(0xFF8b5cf6),
  };

  Future<void> _markComplete() async {
    setState(() => _marking = true);
    try {
      await _api.markComplete(widget.session.id);
      if (mounted) {
        Navigator.pop(context);
        widget.onMarkComplete();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Mislukt: ${e.toString().split('\n').first}')),
        );
      }
    } finally {
      if (mounted) setState(() => _marking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.session;
    final color = _typeColors[s.workoutType.toLowerCase()] ?? const Color(0xFF64748b);
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.6,
      maxChildSize: 0.92,
      builder: (_, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Center(
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(color: const Color(0xFF334155), borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 16),
          Row(children: [
            Container(width: 4, height: 40, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(2))),
            const SizedBox(width: 12),
            Expanded(
              child: Text(s.title,
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            ),
            if (s.isCompleted)
              const Icon(Icons.check_circle, color: Color(0xFF22c55e), size: 24),
          ]),
          if (s.scheduledDate != null) ...[
            const SizedBox(height: 4),
            Text(DateFormat('EEEE d MMMM yyyy', 'nl').format(s.scheduledDate!),
                style: const TextStyle(color: Color(0xFF64748b), fontSize: 13)),
          ],
          const SizedBox(height: 20),
          Row(children: [
            if (s.distanceKm != null) _InfoChip(Icons.route, '${s.distanceKm} km'),
            if (s.durationMinutes != null) ...[
              const SizedBox(width: 10),
              _InfoChip(Icons.timer, '${s.durationMinutes} min'),
            ],
          ]),
          if (s.notes != null && s.notes!.isNotEmpty) ...[
            const SizedBox(height: 20),
            const Text('Beschrijving', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            Text(s.notes!, style: const TextStyle(color: Color(0xFFcbd5e1), fontSize: 13, height: 1.6)),
          ],
          if (!s.isCompleted) ...[
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _marking ? null : _markComplete,
                icon: _marking
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.check),
                label: Text(_marking ? 'Bezig...' : 'Markeer als voltooid'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366f1),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoChip(this.icon, this.label);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0f172a),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 15, color: const Color(0xFF6366f1)),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
        ]),
      );
}
