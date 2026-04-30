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

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    _load();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
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
                          onPageChanged: (idx) =>
                              setState(() => _selectedWeek = _weeks[idx]),
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
                                  _buildWeekHeader(sessions),
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

  Widget _buildWeekHeader(List<WorkoutSession> sessions) {
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
  final VoidCallback onEdited;
  const _SessionDetailSheet({required this.session, required this.onMarkComplete, required this.onEdited});

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
    return paces.entries.map((e) {
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

  Widget _buildIntervalRow(Map<String, dynamic> iv, Color color) {
    final reps = iv['reps'];
    final dist = iv['distance_m'];
    final pace = iv['pace'];
    final rest = iv['rest_seconds'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF0f172a),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            Container(
              width: 32, height: 32,
              decoration: BoxDecoration(color: color.withOpacity(0.15), shape: BoxShape.circle),
              child: Center(
                child: Text('$reps×', style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('$dist m @ $pace /km',
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                  if (rest != null)
                    Text('Rust: ${rest}s', style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
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
          ],
          if (s.intervals != null && s.intervals!.isNotEmpty) ...[
            const SizedBox(height: 20),
            const Text('Intervallen', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
            const SizedBox(height: 8),
            ...s.intervals!.map((iv) => _buildIntervalRow(iv as Map<String, dynamic>, color)),
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
