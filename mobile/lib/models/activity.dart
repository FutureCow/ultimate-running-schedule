class ActivitySummary {
  final String activityId;
  final String name;
  final String startTime;
  final double distanceKm;
  final int durationSeconds;
  final String? avgPacePerKm;
  final int? avgHeartRate;
  final int? maxHeartRate;
  final int? avgCadence;
  final double? elevationGainM;

  const ActivitySummary({
    required this.activityId,
    required this.name,
    required this.startTime,
    required this.distanceKm,
    required this.durationSeconds,
    this.avgPacePerKm,
    this.avgHeartRate,
    this.maxHeartRate,
    this.avgCadence,
    this.elevationGainM,
  });

  factory ActivitySummary.fromJson(Map<String, dynamic> j) => ActivitySummary(
        activityId: j['activity_id']?.toString() ?? '',
        name: j['name'] ?? j['activity_name'] ?? '',
        startTime: j['start_time'] ?? '',
        distanceKm: (j['distance_km'] as num?)?.toDouble() ?? 0,
        durationSeconds: (j['duration_seconds'] as num?)?.toInt() ?? 0,
        avgPacePerKm: j['avg_pace_per_km'],
        avgHeartRate: j['avg_heart_rate'],
        maxHeartRate: j['max_heart_rate'],
        avgCadence: j['avg_cadence'],
        elevationGainM: (j['elevation_gain_m'] as num?)?.toDouble(),
      );
}

class ActivityDetail {
  final ActivitySummary summary;
  final ActivityStreams streams;
  final List<GpsPoint> gpsTrack;
  final String? aiFeedback;
  final String? sessionTitle;

  const ActivityDetail({
    required this.summary,
    required this.streams,
    required this.gpsTrack,
    this.aiFeedback,
    this.sessionTitle,
  });

  factory ActivityDetail.fromJson(Map<String, dynamic> j) => ActivityDetail(
        summary: ActivitySummary.fromJson(j['summary'] ?? {}),
        streams: ActivityStreams.fromJson(j['streams'] ?? {}),
        gpsTrack: (j['gps_track'] as List? ?? [])
            .map((p) => GpsPoint.fromJson(p))
            .toList(),
        aiFeedback: j['ai_feedback'],
        sessionTitle: j['session_title'],
      );
}

class ActivityStreams {
  final List<int> time;
  final List<double?> pace;
  final List<int?> heartRate;
  final List<int?> cadence;
  final List<double?> altitude;

  const ActivityStreams({
    required this.time,
    required this.pace,
    required this.heartRate,
    required this.cadence,
    required this.altitude,
  });

  factory ActivityStreams.fromJson(Map<String, dynamic> j) => ActivityStreams(
        time: List<int>.from(j['time'] ?? []),
        pace: List<double?>.from(
            (j['pace'] ?? []).map((v) => v != null ? (v as num).toDouble() : null)),
        heartRate: List<int?>.from(
            (j['heart_rate'] ?? []).map((v) => v != null ? (v as num).toInt() : null)),
        cadence: List<int?>.from(
            (j['cadence'] ?? []).map((v) => v != null ? (v as num).toInt() : null)),
        altitude: List<double?>.from(
            (j['altitude'] ?? []).map((v) => v != null ? (v as num).toDouble() : null)),
      );

  bool get hasHeartRate => heartRate.any((v) => v != null);
  bool get hasPace => pace.any((v) => v != null);
  bool get hasCadence => cadence.any((v) => v != null);
  bool get hasAltitude => altitude.any((v) => v != null);
}

class GpsPoint {
  final double lat;
  final double lon;
  final double? altitude;

  const GpsPoint({required this.lat, required this.lon, this.altitude});

  factory GpsPoint.fromJson(Map<String, dynamic> j) => GpsPoint(
        lat: (j['lat'] as num).toDouble(),
        lon: (j['lon'] as num).toDouble(),
        altitude: (j['altitude'] as num?)?.toDouble(),
      );
}
