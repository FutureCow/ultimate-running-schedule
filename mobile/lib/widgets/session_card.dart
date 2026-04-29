import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/plan.dart';

const _typeColors = {
  'easy': Color(0xFF22c55e),
  'easy_run': Color(0xFF22c55e),
  'recovery': Color(0xFF22c55e),
  'tempo': Color(0xFFf59e0b),
  'interval': Color(0xFFef4444),
  'long': Color(0xFF6366f1),
  'long_run': Color(0xFF6366f1),
  'rest': Color(0xFF64748b),
  'race': Color(0xFFec4899),
  'strength': Color(0xFF8b5cf6),
};

const _typeLabels = {
  'easy': 'Rustig',
  'easy_run': 'Rustig',
  'recovery': 'Herstel',
  'tempo': 'Tempo',
  'interval': 'Interval',
  'long': 'Lang',
  'long_run': 'Lang',
  'rest': 'Rust',
  'race': 'Wedstrijd',
  'strength': 'Kracht',
};

class SessionCard extends StatelessWidget {
  final WorkoutSession session;
  final VoidCallback? onTap;

  const SessionCard({super.key, required this.session, this.onTap});

  @override
  Widget build(BuildContext context) {
    final color = _typeColors[session.workoutType.toLowerCase()] ?? const Color(0xFF64748b);
    final label = _typeLabels[session.workoutType.toLowerCase()] ?? session.workoutType;
    final date = session.scheduledDate;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: const Color(0xFF1e293b),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: session.isCompleted ? color.withOpacity(0.3) : Colors.transparent,
          ),
        ),
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 4,
              height: 48,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: color.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(label,
                            style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600)),
                      ),
                      const SizedBox(width: 8),
                      if (date != null)
                        Text(
                          DateFormat('EEE d MMM', 'nl').format(date),
                          style: const TextStyle(color: Color(0xFF64748b), fontSize: 11),
                        ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(session.title,
                      style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                  if (session.distanceKm != null || session.durationMinutes != null)
                    Text(
                      [
                        if (session.distanceKm != null) '${session.distanceKm} km',
                        if (session.durationMinutes != null) '${session.durationMinutes} min',
                      ].join(' · '),
                      style: const TextStyle(color: Color(0xFF64748b), fontSize: 12),
                    ),
                ],
              ),
            ),
            if (session.isCompleted)
              const Icon(Icons.check_circle, color: Color(0xFF22c55e), size: 20)
            else
              const Icon(Icons.chevron_right, color: Color(0xFF334155), size: 20),
          ],
        ),
      ),
    );
  }
}
