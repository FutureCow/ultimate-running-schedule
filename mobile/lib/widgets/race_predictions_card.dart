import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Estimated 5K/10K/HM/M times from GET /garmin/race-predictions,
/// with the run they rest on.
class RacePredictionsCard extends StatelessWidget {
  final Map<String, dynamic> data;

  const RacePredictionsCard({super.key, required this.data});

  static const _labels = {
    '5k': '5K',
    '10k': '10K',
    'half_marathon': 'Halve',
    'marathon': 'Marathon',
  };

  static String _clock(num seconds) {
    final total = seconds.round();
    final h = total ~/ 3600;
    final m = (total % 3600) ~/ 60;
    final s = total % 60;
    final ss = s.toString().padLeft(2, '0');
    if (h > 0) return '$h:${m.toString().padLeft(2, '0')}:$ss';
    return '$m:$ss';
  }

  String _basisLine() {
    final basis = data['basis'] as Map<String, dynamic>? ?? {};
    final name = (basis['name'] as String?)?.trim();
    String date = basis['date'] as String? ?? '';
    try {
      date = DateFormat('d MMM yyyy', 'nl').format(DateTime.parse(date));
    } catch (_) {}
    final km = (basis['distance_km'] as num? ?? 0)
        .toStringAsFixed(2)
        .replaceFirst(RegExp(r'\.?0+$'), '')
        .replaceAll('.', ',');
    final time = _clock(basis['duration_seconds'] as num? ?? 0);
    return 'Op basis van: ${name == null || name.isEmpty ? '—' : name}, $date ($km km in $time)';
  }

  @override
  Widget build(BuildContext context) {
    final predictions = (data['predictions'] as List? ?? []).cast<Map<String, dynamic>>();
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1e293b),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.emoji_events_outlined, size: 18, color: Color(0xFF818cf8)),
              SizedBox(width: 8),
              Text('Geschatte wedstrijdtijden',
                  style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              for (var i = 0; i < predictions.length; i++) ...[
                if (i > 0) const SizedBox(width: 6),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF334155),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_labels[predictions[i]['key']] ?? '${predictions[i]['key']}',
                            style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 11)),
                        const SizedBox(height: 2),
                        FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(_clock(predictions[i]['seconds'] as num? ?? 0),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                fontWeight: FontWeight.w600,
                                fontFeatures: [FontFeature.tabularFigures()],
                              )),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          Text(_basisLine(), style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 12)),
          const SizedBox(height: 4),
          const Text(
            'Uit je snelste run van minstens 3 km in de laatste 12 weken. '
            'De marathontijd geldt alleen als je ook voor die afstand getraind hebt.',
            style: TextStyle(color: Color(0xFF64748b), fontSize: 10),
          ),
        ],
      ),
    );
  }
}
