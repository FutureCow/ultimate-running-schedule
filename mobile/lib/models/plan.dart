class Plan {
  final int id;
  final String publicId;
  final String title;
  final String status;
  final int weekCount;
  final DateTime createdAt;
  final List<WorkoutSession> sessions;
  final String? goal;
  final int? targetTimeSeconds;
  final String? targetPacePerKm;
  final DateTime? startDate;
  final DateTime? raceDate;
  final double? weeklyKm;
  final Map<String, dynamic>? paceZones;

  const Plan({
    required this.id,
    required this.publicId,
    required this.title,
    required this.status,
    required this.weekCount,
    required this.createdAt,
    required this.sessions,
    this.goal,
    this.targetTimeSeconds,
    this.targetPacePerKm,
    this.startDate,
    this.raceDate,
    this.weeklyKm,
    this.paceZones,
  });

  factory Plan.fromJson(Map<String, dynamic> j) {
    final planJson = j['plan_json'] as Map<String, dynamic>?;
    final overview = planJson?['plan_overview'] as Map<String, dynamic>?;
    final paceZones = overview?['pace_zones'] as Map<String, dynamic>?;
    return Plan(
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
      goal: j['goal'] as String?,
      targetTimeSeconds: (j['target_time_seconds'] as num?)?.toInt(),
      targetPacePerKm: j['target_pace_per_km'] as String?,
      startDate: j['start_date'] != null ? DateTime.tryParse(j['start_date']) : null,
      raceDate: j['race_date'] != null ? DateTime.tryParse(j['race_date']) : null,
      weeklyKm: (j['weekly_km'] as num?)?.toDouble(),
      paceZones: paceZones,
    );
  }

  String get formattedGoal {
    const labels = {
      '5km': '5 km', '10km': '10 km', 'half_marathon': 'Halve marathon',
      'marathon': 'Marathon', 'base_building': 'Basisconditie', 'fitness': 'Conditie',
    };
    return labels[goal?.toLowerCase()] ?? goal ?? '';
  }

  String get formattedTargetTime {
    if (targetTimeSeconds == null) return '';
    final h = targetTimeSeconds! ~/ 3600;
    final m = (targetTimeSeconds! % 3600) ~/ 60;
    final s = targetTimeSeconds! % 60;
    if (h > 0) return '${h}u ${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
    return '${m}:${s.toString().padLeft(2, '0')}';
  }
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
  final String? garminWorkoutId;
  final DateTime? garminPushedAt;
  final String? aiInsights;
  final Map<String, dynamic>? paces;
  final List<dynamic>? intervals;

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
    this.garminWorkoutId,
    this.garminPushedAt,
    this.aiInsights,
    this.paces,
    this.intervals,
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
        garminWorkoutId: j['garmin_workout_id']?.toString(),
        garminPushedAt: j['garmin_pushed_at'] != null ? DateTime.tryParse(j['garmin_pushed_at']) : null,
        aiInsights: j['ai_insights'] as String?,
        paces: j['target_paces'] as Map<String, dynamic>?,
        intervals: j['intervals'] as List<dynamic>?,
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
