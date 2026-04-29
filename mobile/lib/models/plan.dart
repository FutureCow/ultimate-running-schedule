class Plan {
  final int id;
  final String publicId;
  final String title;
  final String status;
  final int weekCount;
  final DateTime createdAt;
  final List<WorkoutSession> sessions;

  const Plan({
    required this.id,
    required this.publicId,
    required this.title,
    required this.status,
    required this.weekCount,
    required this.createdAt,
    required this.sessions,
  });

  factory Plan.fromJson(Map<String, dynamic> j) => Plan(
        id: (j['id'] as num?)?.toInt() ?? 0,
        publicId: j['public_id'] as String? ?? '',
        title: j['name'] as String? ?? j['title'] as String? ?? '',
        status: j['status'] as String? ?? 'active',
        weekCount: (j['duration_weeks'] as num?)?.toInt() ??
            (j['week_count'] as num?)?.toInt() ?? 12,
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
        id: (j['id'] as num?)?.toInt() ?? 0,
        weekNumber: (j['week_number'] as num?)?.toInt() ?? 1,
        dayNumber: (j['day_number'] as num?)?.toInt() ?? 1,
        title: j['title'] as String? ?? '',
        workoutType: j['workout_type'] as String? ?? 'easy',
        distanceKm: (j['distance_km'] as num?)?.toDouble(),
        durationMinutes: (j['duration_minutes'] as num?)?.toInt(),
        notes: j['description'] as String? ?? j['notes'] as String?,
        isCompleted: j['completed_at'] != null || j['is_completed'] == true,
        scheduledDate: j['scheduled_date'] != null
            ? DateTime.tryParse(j['scheduled_date'])
            : null,
        garminActivityId: j['garmin_activity_id']?.toString(),
        aiInsights: j['ai_insights'] as String?,
      );

  String get typeColor {
    switch (workoutType.toLowerCase()) {
      case 'easy':
      case 'easy_run':
      case 'recovery': return '#22c55e';
      case 'tempo': return '#f59e0b';
      case 'interval': return '#ef4444';
      case 'long':
      case 'long_run': return '#6366f1';
      case 'rest': return '#64748b';
      case 'strength': return '#8b5cf6';
      case 'race': return '#ec4899';
      default: return '#64748b';
    }
  }
}
