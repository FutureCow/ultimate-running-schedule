import 'package:flutter/material.dart';
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
  int _selectedWeek = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; });
    try {
      final res = await _api.getPlans();
      final plans = (res.data as List).map((p) => Plan.fromJson(p)).toList();
      final active = plans.where((p) => p.status == 'active').toList();
      final plan = active.isNotEmpty ? active.first : (plans.isNotEmpty ? plans.first : null);
      if (plan != null) {
        final detail = await _api.getPlan(plan.id);
        final fullPlan = Plan.fromJson(detail.data);
        final currentWeek = _detectCurrentWeek(fullPlan);
        setState(() { _plan = fullPlan; _selectedWeek = currentWeek; });
      }
    } catch (_) {
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
                                    child: SessionCard(session: s),
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
