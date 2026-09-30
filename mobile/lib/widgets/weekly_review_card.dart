import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// The weekly look back at a plan under way, folded so it does not push the
/// week's sessions off the screen — except the first time a week's review is
/// seen. Collapsed it shows the title and the key numbers; expanded, volume
/// per week and — for Elite — the narrative.
class WeeklyReviewCard extends StatefulWidget {
  final int planId;
  final Map<String, dynamic> review;

  const WeeklyReviewCard({super.key, required this.planId, required this.review});

  static String _km(num value) =>
      value.toStringAsFixed(1).replaceAll(RegExp(r'\.0$'), '').replaceAll('.', ',');

  @override
  State<WeeklyReviewCard> createState() => _WeeklyReviewCardState();
}

class _WeeklyReviewCardState extends State<WeeklyReviewCard> {
  final _controller = ExpansionTileController();

  @override
  void initState() {
    super.initState();
    _openIfNew();
  }

  Future<void> _openIfNew() async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'weekly_review_seen_${widget.planId}';
    final week = widget.review['week'] as int?;
    if (week == null || prefs.getInt(key) == week) return;
    await prefs.setInt(key, week);
    if (mounted) _controller.expand();
  }

  @override
  Widget build(BuildContext context) {
    final review = widget.review;
    const km = WeeklyReviewCard._km;
    final stats = (review['stats'] as Map?)?.cast<String, dynamic>() ?? {};
    final weeks = ((stats['weeks'] as List?) ?? [])
        .map((w) => (w as Map).cast<String, dynamic>())
        .toList();
    final text = review['text'] as String?;
    final peak = weeks.fold<double>(1, (m, w) {
      final planned = (w['planned_km'] as num?)?.toDouble() ?? 0;
      final run = (w['run_km'] as num?)?.toDouble() ?? 0;
      return [m, planned, run].reduce((a, b) => a > b ? a : b);
    }) * 1.1; // headroom so nothing touches the end of the track

    final facts = <String>[
      'Nog ${stats['weeks_to_go'] ?? '?'} weken',
      if (stats['longest_run_km'] != null) 'langste duurloop ${km(stats['longest_run_km'])} km',
      if (stats['longest_ahead_km'] != null) 'straks ${km(stats['longest_ahead_km'])} km',
    ];
    final eff = (stats['aerobic_efficiency'] as Map?)?.cast<String, dynamic>();
    if (eff != null) {
      final pct = (eff['change_pct'] as num).toDouble();
      facts.add(pct >= 0
          ? 'rustige runs ${km(pct)}% efficiënter'
          : 'rustige runs ${km(-pct)}% minder efficiënt');
    }

    return Card(
      color: const Color(0xFF1e293b),
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          controller: _controller,
          leading: const Icon(Icons.auto_awesome, color: Color(0xFF6366f1), size: 20),
          title: Text('Terugblik week ${review['week']}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
          subtitle: Text(facts.join(' · '),
              style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 11)),
          iconColor: const Color(0xFF94a3b8),
          collapsedIconColor: const Color(0xFF94a3b8),
          childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
          children: [
            // The card sits above the week's sessions rather than inside a
            // scroll view, so its content scrolls on its own instead of
            // running off the bottom of the screen
            ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.45),
              child: Scrollbar(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final w in weeks) _WeekBar(week: w, peak: peak),
                      const Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Text('Groen: gelopen · streepje: gepland',
                            style: TextStyle(color: Color(0xFF64748b), fontSize: 10)),
                      ),
                      if (text != null && text.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Text(text,
                            style: const TextStyle(
                                color: Color(0xFFcbd5e1), fontSize: 13, height: 1.45)),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WeekBar extends StatelessWidget {
  final Map<String, dynamic> week;
  final double peak;

  const _WeekBar({required this.week, required this.peak});

  @override
  Widget build(BuildContext context) {
    final planned = (week['planned_km'] as num?)?.toDouble() ?? 0;
    final run = (week['run_km'] as num?)?.toDouble() ?? 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          SizedBox(
            width: 54,
            child: Text('Week ${week['week']}',
                style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
          ),
          Expanded(
            child: LayoutBuilder(
              builder: (_, box) => SizedBox(
                height: 14,
                child: Stack(alignment: Alignment.centerLeft, children: [
                  Container(height: 8, decoration: _bar(const Color(0xFF334155))),
                  Container(height: 8, width: box.maxWidth * run / peak,
                      decoration: _bar(const Color(0xFF22c55e))),
                  // The plan as a marker, visible even when more was run than planned
                  Positioned(
                    left: box.maxWidth * planned / peak - 1,
                    child: Container(width: 2, height: 14, decoration: _bar(const Color(0xFFe2e8f0))),
                  ),
                ]),
              ),
            ),
          ),
          SizedBox(
            width: 92,
            child: Text(
              '${WeeklyReviewCard._km(run)}/${WeeklyReviewCard._km(planned)} km  '
              '${week['sessions_done']}/${week['sessions_planned']}',
              textAlign: TextAlign.right,
              style: const TextStyle(color: Color(0xFFcbd5e1), fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }

  static BoxDecoration _bar(Color color) =>
      BoxDecoration(color: color, borderRadius: BorderRadius.circular(4));
}
