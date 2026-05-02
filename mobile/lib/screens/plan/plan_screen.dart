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
  late final PageController _pageController;
  bool _recalibrating = false;
  final ScrollController _weekScrollController = ScrollController();
  static const double _weekChipWidth = 90.0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _load();
  }

  @override
  void dispose() {
    _pageController.dispose();
    _weekScrollController.dispose();
    super.dispose();
  }

  void _scrollWeekSelectorTo(int weekIndex) {
    if (!_weekScrollController.hasClients) return;
    final offset = (weekIndex * _weekChipWidth) - (_weekScrollController.position.viewportDimension / 2) + (_weekChipWidth / 2);
    _weekScrollController.animateTo(
      offset.clamp(0.0, _weekScrollController.position.maxScrollExtent),
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
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
        final weeks = fullPlan.sessions.map((s) => s.weekNumber).toSet().toList()..sort();
        final pageIndex = weeks.indexOf(currentWeek).clamp(0, weeks.length - 1);
        setState(() { _plan = fullPlan; _selectedWeek = currentWeek; });
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_pageController.hasClients) {
            _pageController.jumpToPage(pageIndex);
          }
        });
      }
    } catch (e) {
      setState(() => _error = 'Kon plan niet laden: ${e.toString().split('\n').first}');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _recalibratePaces() async {
    if (_plan == null) return;
    setState(() => _recalibrating = true);
    try {
      final res = await _api.previewRegeneratePlan(_plan!.publicId);
      final preview = res.data as Map<String, dynamic>;
      if (!mounted) return;
      showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: const Color(0xFF1e293b),
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => _PaceZonesPreviewSheet(
          preview: preview,
          onApply: () async {
            Navigator.pop(context);
            setState(() => _recalibrating = true);
            try {
              final applyRes = await _api.regeneratePlan(_plan!.publicId);
              final updatedPlan = Plan.fromJson(applyRes.data);
              setState(() => _plan = updatedPlan);
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                  content: Text('Tempo zones bijgewerkt'),
                  backgroundColor: Color(0xFF1e293b),
                ));
              }
            } catch (e) {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text('Toepassen mislukt: ${e.toString().split('\n').first}'),
                  backgroundColor: const Color(0xFF1e293b),
                ));
              }
            } finally {
              if (mounted) setState(() => _recalibrating = false);
            }
          },
        ),
      );
    } catch (e) {
      final msg = e.toString().contains('400')
          ? 'Geen voltooide trainingen gevonden — voltooi eerst een paar runs via Garmin sync.'
          : 'Preview mislukt: ${e.toString().split('\n').first}';
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(msg), backgroundColor: const Color(0xFF1e293b)),
        );
      }
    } finally {
      if (mounted) setState(() => _recalibrating = false);
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

  Future<void> _resetPlan() async {
    if (_plan == null) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: const Color(0xFF1e293b),
        title: const Text('Heel plan terugzetten?', style: TextStyle(color: Colors.white, fontSize: 16)),
        content: const Text(
          'Alle toekomstige, niet-voltooide workouts worden teruggezet naar de originele AI-waarden. Voltooide trainingen blijven onaangetast.',
          style: TextStyle(color: Color(0xFF94a3b8), fontSize: 13),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogCtx, false), child: const Text('Annuleren')),
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx, true),
            child: const Text('Terugzetten', style: TextStyle(color: Color(0xFFef4444))),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await _api.resetPlan(_plan!.publicId);
      await _load();
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1e293b),
            title: const Text('Plan teruggezet', style: TextStyle(color: Colors.white, fontSize: 16)),
            content: const Text('Het plan is teruggezet naar de originele AI-waarden.',
                style: TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1e293b),
            title: const Text('Fout', style: TextStyle(color: Color(0xFFef4444), fontSize: 16)),
            content: Text('Terugzetten mislukt: ${e.toString().split('\n').first}',
                style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
            ],
          ),
        );
      }
    }
  }

  List<int> get _weeks {
    if (_plan == null) return [];
    return _plan!.sessions.map((s) => s.weekNumber).toSet().toList()..sort();
  }

  void _showBulkEdit() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1e293b),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _BulkEditSheet(
        publicId: _plan!.publicId,
        onApplied: (count) {
          Navigator.pop(context);
          _load();
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$count training(en) bijgewerkt')),
          );
        },
      ),
    );
  }

  void _showSessionDetail(WorkoutSession session) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1e293b),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _SessionDetailSheet(session: session, onMarkComplete: _load, onEdited: _load),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Text(_plan?.title ?? 'Trainingsplan'),
          actions: [
            if (_plan != null) ...[
              if (_recalibrating)
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12),
                  child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                )
              else
                IconButton(
                  icon: const Icon(Icons.speed_outlined),
                  tooltip: 'Tempo zones bijstellen',
                  onPressed: _recalibratePaces,
                ),
              IconButton(
                icon: const Icon(Icons.tune),
                tooltip: 'Bulk bewerken',
                onPressed: () => _showBulkEdit(),
              ),
              PopupMenuButton<String>(
                icon: const Icon(Icons.more_vert),
                color: const Color(0xFF1e293b),
                onSelected: (value) {
                  if (value == 'reset') _resetPlan();
                },
                itemBuilder: (_) => [
                  const PopupMenuItem(
                    value: 'reset',
                    child: Row(children: [
                      Icon(Icons.restart_alt, size: 18, color: Color(0xFFef4444)),
                      SizedBox(width: 10),
                      Text('Plan terugzetten', style: TextStyle(color: Color(0xFFef4444))),
                    ]),
                  ),
                ],
              ),
            ],
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
                        child: PageView.builder(
                          controller: _pageController,
                          itemCount: _weeks.length,
                          onPageChanged: (idx) {
                            setState(() => _selectedWeek = _weeks[idx]);
                            _scrollWeekSelectorTo(idx);
                          },
                          itemBuilder: (_, idx) {
                            final week = _weeks[idx];
                            final sessions = _plan!.sessions
                                .where((s) => s.weekNumber == week)
                                .toList()
                              ..sort((a, b) => a.dayNumber.compareTo(b.dayNumber));
                            return RefreshIndicator(
                              onRefresh: _load,
                              child: ListView(
                                padding: const EdgeInsets.all(16),
                                children: [
                                  _buildWeekHeader(sessions, week),
                                  const SizedBox(height: 12),
                                  ...sessions.map((s) => Padding(
                                        padding: const EdgeInsets.only(bottom: 8),
                                        child: SessionCard(
                                          session: s,
                                          onTap: () => _showSessionDetail(s),
                                        ),
                                      )),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
      );

  Widget _buildWeekSelector() => SizedBox(
        height: 50,
        child: ListView.builder(
          controller: _weekScrollController,
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          itemCount: _weeks.length,
          itemBuilder: (_, i) {
            final w = _weeks[i];
            final selected = w == _selectedWeek;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: GestureDetector(
                onTap: () {
                  final idx = _weeks.indexOf(w);
                  setState(() => _selectedWeek = w);
                  _pageController.animateToPage(idx,
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut);
                  _scrollWeekSelectorTo(idx);
                },
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

  Widget _buildWeekHeader(List<WorkoutSession> sessions, int weekNumber) {
    final done = sessions.where((s) => s.isCompleted).length;
    final totalKm = sessions
        .where((s) => s.distanceKm != null)
        .fold(0.0, (sum, s) => sum + s.distanceKm!);
    final pushable = sessions.where((s) => s.workoutType != 'rest').toList();
    final allPushed = pushable.isNotEmpty && pushable.every((s) => s.garminWorkoutId != null);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1e293b),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(child: _WeekStat(label: 'Trainingen', value: '${sessions.length}')),
              Expanded(child: _WeekStat(label: 'Voltooid', value: '$done/${sessions.length}')),
              Expanded(child: _WeekStat(label: 'Afstand', value: '${totalKm.toStringAsFixed(0)} km')),
            ],
          ),
          if (pushable.isNotEmpty) ...[
            const SizedBox(height: 12),
            _GarminWeekButton(
              planPublicId: _plan!.publicId,
              weekNumber: weekNumber,
              allPushed: allPushed,
              onDone: _load,
            ),
          ],
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
  final VoidCallback onEdited;
  const _SessionDetailSheet({required this.session, required this.onMarkComplete, required this.onEdited});

  @override
  State<_SessionDetailSheet> createState() => _SessionDetailSheetState();
}

class _SessionDetailSheetState extends State<_SessionDetailSheet> {
  final _api = ApiService();
  bool _marking = false;
  bool _resetting = false;
  bool _garminBusy = false;
  String? _garminError;
  late String? _garminWorkoutId;

  @override
  void initState() {
    super.initState();
    _garminWorkoutId = widget.session.garminWorkoutId;
  }

  Future<void> _pushToGarmin() async {
    setState(() { _garminBusy = true; _garminError = null; });
    try {
      final res = await _api.pushSessions([widget.session.id]);
      final results = (res.data['results'] as List?) ?? [];
      final first = results.isNotEmpty ? results.first as Map<String, dynamic> : null;
      if (first?['success'] == true) {
        setState(() => _garminWorkoutId = first!['garmin_workout_id']?.toString() ?? 'pushed');
        widget.onEdited();
      } else {
        setState(() => _garminError = first?['error']?.toString() ?? 'Push mislukt');
      }
    } catch (e) {
      setState(() => _garminError = 'Fout: ${e.toString().split('\n').first}');
    } finally {
      if (mounted) setState(() => _garminBusy = false);
    }
  }

  Future<void> _removeFromGarmin() async {
    setState(() { _garminBusy = true; _garminError = null; });
    try {
      await _api.removeGarminSession(widget.session.id);
      setState(() => _garminWorkoutId = null);
      widget.onEdited();
    } catch (e) {
      setState(() => _garminError = 'Verwijderen mislukt');
    } finally {
      if (mounted) setState(() => _garminBusy = false);
    }
  }

  static const _typeColors = {
    'easy': Color(0xFF22c55e), 'easy_run': Color(0xFF22c55e), 'recovery': Color(0xFF22c55e),
    'tempo': Color(0xFFf59e0b),
    'interval': Color(0xFFef4444),
    'long': Color(0xFF6366f1), 'long_run': Color(0xFF6366f1),
    'rest': Color(0xFF64748b),
    'race': Color(0xFFec4899),
    'strength': Color(0xFF8b5cf6),
  };

  static const _paceLabels = {
    'warmup':  'Warming-up',
    'main':    'Hoofdtempo',
    'cooldown':'Cooling-down',
    'easy':    'Rustig',
    'threshold': 'Drempel',
    'interval': 'Interval',
    'repetition': 'Herhaling',
  };

  List<Widget> _buildPaceRows(Map<String, dynamic> paces, Color color) {
    final entries = paces.entries
        .where((e) => e.key != 'strides' && e.value != null && e.value.toString().isNotEmpty)
        .toList();
    return entries.map((e) {
      final label = _paceLabels[e.key] ?? e.key;
      return Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF0f172a),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
              Text('${e.value} /km',
                  style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      );
    }).toList();
  }

  Widget _buildStrideChip(Map<String, dynamic> st, Color color) {
    final reps = st['reps'];
    final dist = st['distance_m'];
    final pace = st['pace'];
    final rest = st['rest_seconds'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF0f172a),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Text('Strides', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
            if (reps != null) ...[
              const SizedBox(width: 6),
              Text('$reps×', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
            if (dist != null) ...[
              const SizedBox(width: 4),
              Text('${dist}m', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
            if (pace != null) ...[
              const SizedBox(width: 6),
              Text('@ $pace /km', style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 12)),
            ],
            if (rest != null) ...[
              const SizedBox(width: 6),
              Text('· ${rest}s rust', style: const TextStyle(color: Color(0xFF475569), fontSize: 11)),
            ],
          ]),
        ),
      ]),
    );
  }

  Widget _buildIntervalRow(Map<String, dynamic> iv, Color color) {
    final reps = iv['reps'];
    final dist = iv['distance_m'];
    final dur = iv['duration_seconds'];
    final pace = iv['pace'];
    final rest = iv['rest_seconds'];
    final distLabel = dist != null ? '${dist}m' : (dur != null ? '${dur}s' : '');
    return Padding(
      padding: const EdgeInsets.only(bottom: 6, right: 4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF0f172a),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('${reps}×', style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
            if (distLabel.isNotEmpty) ...[
              const SizedBox(width: 4),
              Text(distLabel, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
            ],
            if (pace != null) ...[
              const SizedBox(width: 6),
              Text('@ $pace /km', style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 12)),
            ],
            if (rest != null) ...[
              const SizedBox(width: 6),
              Text('· ${rest}s rust', style: const TextStyle(color: Color(0xFF475569), fontSize: 11)),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _reset() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogCtx) => AlertDialog(
        backgroundColor: const Color(0xFF1e293b),
        title: const Text('Terugzetten naar origineel?', style: TextStyle(color: Colors.white, fontSize: 16)),
        content: const Text('Alle handmatige aanpassingen aan tempo, intervallen en afstand worden ongedaan gemaakt.',
            style: TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogCtx, false), child: const Text('Annuleren')),
          TextButton(
            onPressed: () => Navigator.pop(dialogCtx, true),
            child: const Text('Terugzetten', style: TextStyle(color: Color(0xFFef4444))),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    setState(() => _resetting = true);
    try {
      await _api.resetSession(widget.session.id);
      if (mounted) {
        Navigator.pop(context);
        widget.onEdited();
      }
    } catch (e) {
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1e293b),
            title: const Text('Fout', style: TextStyle(color: Color(0xFFef4444), fontSize: 16)),
            content: Text('Terugzetten mislukt: ${e.toString().split('\n').first}',
                style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 13)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
            ],
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _resetting = false);
    }
  }

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
            if (_resetting)
              const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF64748b)))
            else
              IconButton(
                icon: const Icon(Icons.restart_alt, size: 20, color: Color(0xFF64748b)),
                tooltip: 'Terugzetten naar origineel',
                onPressed: _reset,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            const SizedBox(width: 4),
            IconButton(
              icon: const Icon(Icons.edit_outlined, size: 20, color: Color(0xFF64748b)),
              onPressed: () => showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: const Color(0xFF1e293b),
                shape: const RoundedRectangleBorder(
                  borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                ),
                builder: (_) => _SessionEditForm(
                  session: widget.session,
                  onSaved: () {
                    Navigator.pop(context);
                    Navigator.pop(context);
                    widget.onEdited();
                  },
                ),
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
            if (s.isCompleted) ...[
              const SizedBox(width: 8),
              const Icon(Icons.check_circle, color: Color(0xFF22c55e), size: 24),
            ],
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
          if (s.paces != null && s.paces!.isNotEmpty) ...[
            const SizedBox(height: 20),
            const Text('Tempo', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            ..._buildPaceRows(s.paces!, color),
            if (s.paces!['strides'] is Map) ...[
              const SizedBox(height: 8),
              _buildStrideChip(s.paces!['strides'] as Map<String, dynamic>, color),
            ],
          ],
          if (s.intervals != null && s.intervals!.isNotEmpty) ...[
            const SizedBox(height: 20),
            const Text('Intervallen', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: s.intervals!.map((iv) => _buildIntervalRow(iv as Map<String, dynamic>, color)).toList(),
            ),
          ],
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
          if (s.workoutType != 'rest') ...[
            const SizedBox(height: 10),
            if (_garminError != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_garminError!, style: const TextStyle(color: Colors.red, fontSize: 12)),
              ),
            if (_garminWorkoutId != null)
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _garminBusy ? null : _removeFromGarmin,
                  icon: _garminBusy
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.5))
                      : const Icon(Icons.watch_off_outlined, size: 18),
                  label: const Text('Verwijder van Garmin'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF64748b),
                    side: const BorderSide(color: Color(0xFF334155)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              )
            else
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _garminBusy ? null : _pushToGarmin,
                  icon: _garminBusy
                      ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.5, color: Color(0xFF22d3ee)))
                      : const Icon(Icons.watch_outlined, size: 18, color: Color(0xFF22d3ee)),
                  label: const Text('Push naar Garmin', style: TextStyle(color: Color(0xFF22d3ee))),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0x3022d3ee)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
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

class _SessionEditForm extends StatefulWidget {
  final WorkoutSession session;
  final VoidCallback onSaved;
  const _SessionEditForm({required this.session, required this.onSaved});

  @override
  State<_SessionEditForm> createState() => _SessionEditFormState();
}

class _SessionEditFormState extends State<_SessionEditForm> {
  final _api = ApiService();
  final _formKey = GlobalKey<FormState>();
  bool _saving = false;

  late final TextEditingController _titleCtrl;
  late final TextEditingController _distanceCtrl;
  late final TextEditingController _durationCtrl;
  late final TextEditingController _notesCtrl;
  late DateTime? _selectedDate;
  late final Map<String, TextEditingController> _paceCtrl;

  static const _paceLabels = {
    'warmup':     'Warming-up',
    'main':       'Hoofdtempo',
    'cooldown':   'Cooling-down',
    'easy':       'Rustig',
    'threshold':  'Drempel',
    'interval':   'Interval',
    'repetition': 'Herhaling',
  };

  @override
  void initState() {
    super.initState();
    final s = widget.session;
    _titleCtrl    = TextEditingController(text: s.title);
    _distanceCtrl = TextEditingController(text: s.distanceKm?.toString() ?? '');
    _durationCtrl = TextEditingController(text: s.durationMinutes?.toString() ?? '');
    _notesCtrl    = TextEditingController(text: s.notes ?? '');
    _selectedDate = s.scheduledDate;
    _paceCtrl = {
      for (final e in (s.paces ?? {}).entries)
        e.key: TextEditingController(text: e.value?.toString() ?? ''),
    };
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _distanceCtrl.dispose();
    _durationCtrl.dispose();
    _notesCtrl.dispose();
    for (final c in _paceCtrl.values) c.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: const ColorScheme.dark(primary: Color(0xFF6366f1)),
        ),
        child: child!,
      ),
    );
    if (picked != null) setState(() => _selectedDate = picked);
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final body = <String, dynamic>{};

      final title = _titleCtrl.text.trim();
      if (title.isNotEmpty) body['title'] = title;

      final dist = double.tryParse(_distanceCtrl.text.trim());
      if (dist != null) body['distance_km'] = dist;

      final dur = int.tryParse(_durationCtrl.text.trim());
      if (dur != null) body['duration_minutes'] = dur;

      body['description'] = _notesCtrl.text.trim();

      if (_selectedDate != null && _selectedDate != widget.session.scheduledDate) {
        body['scheduled_date'] =
            '${_selectedDate!.year.toString().padLeft(4, '0')}'
            '-${_selectedDate!.month.toString().padLeft(2, '0')}'
            '-${_selectedDate!.day.toString().padLeft(2, '0')}';
      }

      if (_paceCtrl.isNotEmpty) {
        final paces = <String, String>{
          for (final e in _paceCtrl.entries)
            if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim(),
        };
        body['target_paces'] = paces;
      }

      await _api.updateSessionDetails(widget.session.id, body);
      if (mounted) widget.onSaved();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Opslaan mislukt: ${e.toString().split('\n').first}')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  InputDecoration _dec(String hint, {String? label}) => InputDecoration(
        hintText: hint,
        labelText: label,
        labelStyle: const TextStyle(color: Color(0xFF64748b)),
        hintStyle: const TextStyle(color: Color(0xFF475569), fontSize: 14),
        filled: true,
        fillColor: const Color(0xFF0f172a),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: Color(0xFF334155))),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: Color(0xFF334155))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: Color(0xFF6366f1))),
        errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: Color(0xFFef4444))),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(t,
            style: const TextStyle(
                color: Color(0xFF94a3b8), fontSize: 12, fontWeight: FontWeight.w500)),
      );

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.85,
      maxChildSize: 0.95,
      builder: (_, controller) => Form(
        key: _formKey,
        child: ListView(
          controller: controller,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                decoration: BoxDecoration(
                    color: const Color(0xFF334155),
                    borderRadius: BorderRadius.circular(2)),
              ),
            ),
            const SizedBox(height: 16),
            const Text('Workout bewerken',
                style: TextStyle(
                    color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),

            _label('Titel'),
            TextFormField(
              controller: _titleCtrl,
              style: const TextStyle(color: Colors.white),
              decoration: _dec('Naam van de workout'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Vul een titel in' : null,
            ),
            const SizedBox(height: 16),

            _label('Datum'),
            GestureDetector(
              onTap: _pickDate,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                decoration: BoxDecoration(
                  color: const Color(0xFF0f172a),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(children: [
                  const Icon(Icons.calendar_today, size: 16, color: Color(0xFF6366f1)),
                  const SizedBox(width: 10),
                  Text(
                    _selectedDate != null
                        ? DateFormat('EEEE d MMMM yyyy', 'nl').format(_selectedDate!)
                        : 'Kies een datum',
                    style: TextStyle(
                      color: _selectedDate != null
                          ? Colors.white
                          : const Color(0xFF64748b),
                      fontSize: 14,
                    ),
                  ),
                ]),
              ),
            ),
            const SizedBox(height: 16),

            Row(children: [
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Afstand (km)'),
                  TextFormField(
                    controller: _distanceCtrl,
                    style: const TextStyle(color: Colors.white),
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: _dec('bv. 10.5'),
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return null;
                      return double.tryParse(v.trim()) == null ? 'Ongeldig' : null;
                    },
                  ),
                ],
              )),
              const SizedBox(width: 12),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _label('Duur (min)'),
                  TextFormField(
                    controller: _durationCtrl,
                    style: const TextStyle(color: Colors.white),
                    keyboardType: TextInputType.number,
                    decoration: _dec('bv. 60'),
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) return null;
                      return int.tryParse(v.trim()) == null ? 'Ongeldig' : null;
                    },
                  ),
                ],
              )),
            ]),

            if (_paceCtrl.isNotEmpty) ...[
              const SizedBox(height: 16),
              _label('Tempo (min:sec/km)'),
              ...(_paceCtrl.entries.map((e) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: TextFormField(
                      controller: e.value,
                      style: const TextStyle(color: Colors.white),
                      decoration:
                          _dec('5:10-5:20', label: _paceLabels[e.key] ?? e.key),
                      validator: (v) {
                        if (v == null || v.trim().isEmpty) return null;
                        return RegExp(r'^\d+:\d{2}(-\d+:\d{2})?$')
                                .hasMatch(v.trim())
                            ? null
                            : '5:10 of 5:10-5:20';
                      },
                    ),
                  ))),
            ],

            const SizedBox(height: 16),
            _label('Notities'),
            TextFormField(
              controller: _notesCtrl,
              style: const TextStyle(color: Colors.white),
              maxLines: 3,
              decoration: _dec('Optionele notities'),
            ),
            const SizedBox(height: 28),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366f1),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: _saving
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white))
                    : const Text('Opslaan',
                        style: TextStyle(
                            fontSize: 15, fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Pace zones preview sheet ─────────────────────────────────────────────────

class _PaceZonesPreviewSheet extends StatefulWidget {
  final Map<String, dynamic> preview;
  final Future<void> Function() onApply;
  const _PaceZonesPreviewSheet({required this.preview, required this.onApply});

  @override
  State<_PaceZonesPreviewSheet> createState() => _PaceZonesPreviewSheetState();
}

class _PaceZonesPreviewSheetState extends State<_PaceZonesPreviewSheet> {
  bool _applying = false;

  static const _zoneConfig = [
    {'key': 'easy',       'label': 'Rustig',    'color': Color(0xFF22c55e)},
    {'key': 'marathon',   'label': 'Marathon',  'color': Color(0xFF3b82f6)},
    {'key': 'threshold',  'label': 'Drempel',   'color': Color(0xFFf59e0b)},
    {'key': 'interval',   'label': 'Interval',  'color': Color(0xFFef4444)},
    {'key': 'repetition', 'label': 'Herhaling', 'color': Color(0xFF8b5cf6)},
  ];

  @override
  Widget build(BuildContext context) {
    final current = (widget.preview['current_zones'] as Map?)?.cast<String, dynamic>() ?? {};
    final next    = (widget.preview['new_zones']     as Map?)?.cast<String, dynamic>() ?? {};
    final notes   = widget.preview['notes'] as String?;
    final count   = widget.preview['sessions_to_update'] as int? ?? 0;
    final runs    = widget.preview['based_on_runs']  as int? ?? 0;

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.speed_outlined, color: Color(0xFF6366f1), size: 20),
            const SizedBox(width: 10),
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Tempo zones bijstellen', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                Text('Op basis van $runs activiteiten · $count trainingen worden bijgewerkt',
                    style: const TextStyle(color: Color(0xFF64748b), fontSize: 12)),
              ],
            )),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close, color: Color(0xFF64748b))),
          ]),

          if (notes != null && notes.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1d4ed8).withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF3b82f6).withOpacity(0.2)),
              ),
              child: Text(notes, style: const TextStyle(color: Color(0xFFcbd5e1), fontSize: 12, height: 1.5)),
            ),
          ],

          const SizedBox(height: 16),
          Row(children: [
            const Expanded(child: Text('Huidig', style: TextStyle(color: Color(0xFF64748b), fontSize: 11, fontWeight: FontWeight.w600))),
            const SizedBox(width: 24),
            const Expanded(child: Text('Nieuw', textAlign: TextAlign.right, style: TextStyle(color: Color(0xFF64748b), fontSize: 11, fontWeight: FontWeight.w600))),
          ]),
          const SizedBox(height: 8),

          ..._zoneConfig.map((z) {
            final key   = z['key'] as String;
            final label = z['label'] as String;
            final color = z['color'] as Color;
            final cur   = current[key]?.toString();
            final nxt   = next[key]?.toString();
            if (nxt == null) return const SizedBox.shrink();
            final changed = cur != nxt;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: color.withOpacity(0.18)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 11, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Row(children: [
                      Expanded(
                        child: Text(
                          cur ?? '–',
                          style: TextStyle(
                            color: changed ? const Color(0xFF475569) : color,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            decoration: changed ? TextDecoration.lineThrough : null,
                          ),
                        ),
                      ),
                      if (changed) ...[
                        const Icon(Icons.arrow_forward, size: 14, color: Color(0xFF475569)),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(nxt, textAlign: TextAlign.right,
                              style: TextStyle(color: color, fontSize: 13, fontWeight: FontWeight.bold)),
                        ),
                      ],
                    ]),
                  ],
                ),
              ),
            );
          }),

          const SizedBox(height: 16),
          Row(children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _applying ? null : () => Navigator.pop(context),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFF334155)),
                  padding: const EdgeInsets.symmetric(vertical: 13),
                ),
                child: const Text('Annuleren', style: TextStyle(color: Color(0xFF94a3b8))),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ElevatedButton(
                onPressed: _applying ? null : () async {
                  setState(() => _applying = true);
                  await widget.onApply();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366f1),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 13),
                ),
                child: _applying
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('Toepassen'),
              ),
            ),
          ]),
        ],
      ),
    );
  }
}

// ── Garmin week push button ─────────────────────────────────────────────────

class _GarminWeekButton extends StatefulWidget {
  final String planPublicId;
  final int weekNumber;
  final bool allPushed;
  final VoidCallback onDone;
  const _GarminWeekButton({required this.planPublicId, required this.weekNumber, required this.allPushed, required this.onDone});

  @override
  State<_GarminWeekButton> createState() => _GarminWeekButtonState();
}

class _GarminWeekButtonState extends State<_GarminWeekButton> {
  final _api = ApiService();
  bool _busy = false;
  String? _error;
  late bool _pushed;

  @override
  void initState() {
    super.initState();
    _pushed = widget.allPushed;
  }

  Future<void> _push() async {
    setState(() { _busy = true; _error = null; });
    try {
      await _api.pushWeek(widget.planPublicId, widget.weekNumber);
      setState(() => _pushed = true);
      widget.onDone();
    } catch (e) {
      setState(() => _error = 'Push mislukt');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      if (_error != null)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(_error!, style: const TextStyle(color: Colors.red, fontSize: 11), textAlign: TextAlign.center),
        ),
      OutlinedButton.icon(
        onPressed: _busy ? null : (_pushed ? null : _push),
        icon: _busy
            ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 1.5, color: Color(0xFF22d3ee)))
            : Icon(
                _pushed ? Icons.watch_later : Icons.watch_outlined,
                size: 16,
                color: _pushed ? const Color(0xFF22c55e) : const Color(0xFF22d3ee),
              ),
        label: Text(
          _busy ? 'Bezig...' : (_pushed ? 'Week gepusht naar Garmin' : 'Push week naar Garmin'),
          style: TextStyle(
            fontSize: 13,
            color: _pushed ? const Color(0xFF22c55e) : const Color(0xFF22d3ee),
          ),
        ),
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: _pushed ? const Color(0x3022c55e) : const Color(0x3022d3ee)),
          padding: const EdgeInsets.symmetric(vertical: 10),
        ),
      ),
    ],
  );
}

// ── Bulk edit sheet ────────────────────────────────────────────────────────

class _BulkEditSheet extends StatefulWidget {
  final String publicId;
  final void Function(int count) onApplied;
  const _BulkEditSheet({required this.publicId, required this.onApplied});

  @override
  State<_BulkEditSheet> createState() => _BulkEditSheetState();
}

class _BulkEditSheetState extends State<_BulkEditSheet> {
  final _api = ApiService();
  bool _saving = false;

  int? _filterDay;
  String? _filterType;
  bool _onlyFuture = true;

  // action: 'move' or 'pace'
  String _action = 'move';
  int? _targetDay;
  String _paceKey = 'main';
  final _paceCtrl = TextEditingController();
  String _paceError = '';

  static const _days = ['Ma', 'Di', 'Wo', 'Do', 'Vr', 'Za', 'Zo'];
  static const _types = [
    ('easy_run', 'Easy Run'), ('long_run', 'Long Run'), ('tempo', 'Tempo'),
    ('interval', 'Interval'), ('recovery', 'Herstel'), ('strength', 'Kracht'),
  ];
  static const _paceKeys = [
    ('main', 'Hoofdtempo'), ('warmup', 'Warming-up'), ('cooldown', 'Cooling-down'),
  ];

  @override
  void dispose() { _paceCtrl.dispose(); super.dispose(); }

  bool get _canApply {
    if (_filterDay == null && _filterType == null) return false;
    if (_action == 'move') return _targetDay != null;
    return _paceCtrl.text.trim().isNotEmpty;
  }

  Future<void> _apply() async {
    if (_action == 'pace') {
      final v = _paceCtrl.text.trim();
      if (!RegExp(r'^\d+:\d{2}(-\d+:\d{2})?$').hasMatch(v)) {
        setState(() => _paceError = 'Formaat: 5:10 of 5:10-5:20');
        return;
      }
    }
    setState(() => _saving = true);
    try {
      final filter = <String, dynamic>{'only_future': _onlyFuture};
      if (_filterDay != null) filter['day_number'] = _filterDay;
      if (_filterType != null) filter['workout_type'] = _filterType;

      final Map<String, dynamic> update;
      if (_action == 'move') {
        update = {'day_number': _targetDay};
      } else {
        update = {'target_pace_key': _paceKey, 'target_pace_value': _paceCtrl.text.trim()};
      }

      final res = await _api.bulkEditSessions(widget.publicId, filter, update);
      final count = (res.data['updated'] as num?)?.toInt() ?? 0;
      widget.onApplied(count);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Mislukt: ${e.toString().split('\n').first}')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Widget _chip(String label, bool selected, VoidCallback onTap) => GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFF6366f1).withOpacity(0.2) : const Color(0xFF0f172a),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? const Color(0xFF6366f1) : const Color(0xFF334155),
            ),
          ),
          child: Text(label,
              style: TextStyle(
                  color: selected ? const Color(0xFF818cf8) : const Color(0xFF64748b),
                  fontSize: 12,
                  fontWeight: FontWeight.w600)),
        ),
      );

  Widget _section(String title, Widget child) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  color: Color(0xFF94a3b8), fontSize: 11,
                  fontWeight: FontWeight.w600, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          child,
        ],
      );

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.8,
      maxChildSize: 0.95,
      builder: (_, controller) => ListView(
        controller: controller,
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
        children: [
          Center(child: Container(
            width: 40, height: 4,
            decoration: BoxDecoration(color: const Color(0xFF334155), borderRadius: BorderRadius.circular(2)),
          )),
          const SizedBox(height: 16),
          const Text('Bulk bewerken',
              style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),

          _section('Filter op dag', Wrap(spacing: 6, runSpacing: 6, children: [
            for (int i = 0; i < _days.length; i++)
              _chip(_days[i], _filterDay == i + 1,
                  () => setState(() => _filterDay = _filterDay == i + 1 ? null : i + 1)),
          ])),
          const SizedBox(height: 16),

          _section('Filter op type', Wrap(spacing: 6, runSpacing: 6, children: [
            for (final (key, label) in _types)
              _chip(label, _filterType == key,
                  () => setState(() => _filterType = _filterType == key ? null : key)),
          ])),
          const SizedBox(height: 12),

          Row(children: [
            Checkbox(
              value: _onlyFuture,
              onChanged: (v) => setState(() => _onlyFuture = v ?? true),
              activeColor: const Color(0xFF6366f1),
            ),
            const Expanded(
              child: Text('Alleen toekomstige trainingen',
                  style: TextStyle(color: Color(0xFFcbd5e1), fontSize: 13)),
            ),
          ]),

          const Divider(color: Color(0xFF1e293b), height: 28),

          _section('Actie', Row(children: [
            Expanded(child: _chip('Verplaats naar dag', _action == 'move',
                () => setState(() => _action = 'move'))),
            const SizedBox(width: 8),
            Expanded(child: _chip('Tempo aanpassen', _action == 'pace',
                () => setState(() => _action = 'pace'))),
          ])),
          const SizedBox(height: 16),

          if (_action == 'move') ...[
            _section('Verplaats naar', Wrap(spacing: 6, runSpacing: 6, children: [
              for (int i = 0; i < _days.length; i++)
                _chip(_days[i], _targetDay == i + 1,
                    () => setState(() => _targetDay = i + 1)),
            ])),
          ] else ...[
            _section('Welk tempo', Wrap(spacing: 6, runSpacing: 6, children: [
              for (final (key, label) in _paceKeys)
                _chip(label, _paceKey == key,
                    () => setState(() => _paceKey = key)),
            ])),
            const SizedBox(height: 12),
            TextField(
              controller: _paceCtrl,
              style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
              keyboardType: TextInputType.text,
              onChanged: (_) => setState(() => _paceError = ''),
              decoration: InputDecoration(
                hintText: '6:50-7:00',
                hintStyle: const TextStyle(color: Color(0xFF475569)),
                suffixText: '/km',
                suffixStyle: const TextStyle(color: Color(0xFF64748b)),
                errorText: _paceError.isEmpty ? null : _paceError,
                filled: true,
                fillColor: const Color(0xFF0f172a),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF334155)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF334155)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF6366f1)),
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
          ],

          const SizedBox(height: 28),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: (_saving || !_canApply) ? null : _apply,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366f1),
                foregroundColor: Colors.white,
                disabledBackgroundColor: const Color(0xFF6366f1).withOpacity(0.4),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: _saving
                  ? const SizedBox(width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Toepassen',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
            ),
          ),
        ],
      ),
    );
  }
}
