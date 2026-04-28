class Plan {
  final int id;
  final String title;
  final String status;
  final int weekCount;
  final DateTime createdAt;
  final List<WorkoutSession> sessions;

  const Plan({
    required this.id,
    required this.title,
    required this.status,
    required this.weekCount,
    required this.createdAt,
    required this.sessions,
  });

  factory Plan.fromJson(Map<String, dynamic> j) => Plan(
        id: j['id'],
        title: j['title'] ?? '',
        status: j['status'] ?? 'active',
        weekCount: j['week_count'] ?? 12,
        createdAt: DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
        sessions: (j['sessions'] as List? ?? [])
            .map((s) => WorkoutSession.fromJson(s))
            .toList(),
      );
}

class WorkoutSession {
  final int id;
  final int weekNumber;
  final int dayNumber;
  final String title;
  final String workoutType;
  final double? distanceKm;
  final int? durationMinutes;
  final String? notes;
  final bool isCompleted;
  final DateTime? scheduledDate;
  final String? garminActivityId;
  final String? aiInsights;

  const WorkoutSession({
    required this.id,
    required this.weekNumber,
    required this.dayNumber,
    required this.title,
    required this.workoutType,
    this.distanceKm,
    this.durationMinutes,
    this.notes,
    required this.isCompleted,
    this.scheduledDate,
    this.garminActivityId,
    this.aiInsights,
  });

  factory WorkoutSession.fromJson(Map<String, dynamic> j) => WorkoutSession(
        id: j['id'],
        weekNumber: j['week_number'] ?? 1,
        dayNumber: j['day_number'] ?? 1,
        title: j['title'] ?? '',
        workoutType: j['workout_type'] ?? 'easy',
        distanceKm: (j['distance_km'] as num?)?.toDouble(),
        durationMinutes: j['duration_minutes'],
        notes: j['notes'],
        isCompleted: j['is_completed'] == true || j['completed_at'] != null,
        scheduledDate: DateTime.tryParse(j['scheduled_date'] ?? ''),
        garminActivityId: j['garmin_activity_id']?.toString(),
        aiInsights: j['ai_insights'],
      );

  String get typeColor {
    switch (workoutType.toLowerCase()) {
      case 'easy': return '#22c55e';
      case 'tempo': return '#f59e0b';
      case 'interval': return '#ef4444';
      case 'long': return '#6366f1';
      case 'rest': return '#64748b';
      default: return '#64748b';
    }
  }
}
