import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../services/api_service.dart';

class FriendActivitiesScreen extends StatefulWidget {
  final int friendId;
  final String friendName;
  final String? friendAvatarUrl;
  const FriendActivitiesScreen({super.key, required this.friendId, required this.friendName, this.friendAvatarUrl});
  @override
  State<FriendActivitiesScreen> createState() => _FriendActivitiesScreenState();
}

class _FriendActivitiesScreenState extends State<FriendActivitiesScreen> {
  final _api = ApiService();
  List<dynamic> _activities = [];
  bool _loading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = ''; });
    try {
      final res = await _api.getFriendActivities(widget.friendId);
      setState(() => _activities = (res.data['activities'] as List? ?? []));
    } catch (_) {
      if (mounted) setState(() => _error = 'Activiteiten laden mislukt.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _fmtDuration(int secs) {
    final h = secs ~/ 3600;
    final m = (secs % 3600) ~/ 60;
    final s = secs % 60;
    if (h > 0) return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  String _fmtDate(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso.replaceFirst(' ', 'T'));
      return DateFormat('EEE d MMM, HH:mm', 'nl').format(dt);
    } catch (_) {
      return iso.length > 10 ? iso.substring(0, 10) : iso;
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Row(
            children: [
              _FriendAvatar(avatarUrl: widget.friendAvatarUrl, name: widget.friendName, radius: 17),
              const SizedBox(width: 10),
              Expanded(
                child: Text(widget.friendName,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    overflow: TextOverflow.ellipsis),
              ),
            ],
          ),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(child: Text(_error, style: const TextStyle(color: Colors.redAccent)))
                : _activities.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.directions_run, size: 64, color: Color(0xFF334155)),
                            const SizedBox(height: 16),
                            const Text('Geen activiteiten gevonden',
                                style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _activities.length,
                          itemBuilder: (_, i) {
                            final a = _activities[i] as Map<String, dynamic>;
                            final actName = (a['activity_name'] as String?)?.isNotEmpty == true
                                ? a['activity_name'] as String
                                : (a['name'] as String?) ?? 'Hardlooptraining';
                            final distKm = a['distance_meters'] != null
                                ? ((a['distance_meters'] as num) / 1000).toStringAsFixed(2)
                                : null;
                            final dur = a['duration_seconds'] != null
                                ? _fmtDuration((a['duration_seconds'] as num).toInt())
                                : null;
                            final pace = a['avg_pace_sec_per_km'];

                            return GestureDetector(
                              onTap: () => context.push(
                                '/friends/${widget.friendId}/${a['activity_id']}',
                                extra: widget.friendName,
                              ),
                              child: Container(
                                margin: const EdgeInsets.only(bottom: 10),
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  color: const Color(0xFF1e293b),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Row(
                                  children: [
                                    Container(
                                      width: 44,
                                      height: 44,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF6366f1).withOpacity(0.15),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: const Icon(Icons.directions_run, color: Color(0xFF6366f1), size: 22),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(actName,
                                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
                                              maxLines: 1, overflow: TextOverflow.ellipsis),
                                          const SizedBox(height: 2),
                                          Text(_fmtDate(a['start_time']?.toString()),
                                              style: const TextStyle(color: Color(0xFF64748b), fontSize: 12)),
                                          const SizedBox(height: 4),
                                          Row(
                                            children: [
                                              if (distKm != null) ...[
                                                _Chip(Icons.route, '$distKm km'),
                                                const SizedBox(width: 8),
                                              ],
                                              if (dur != null) ...[
                                                _Chip(Icons.timer, dur),
                                                const SizedBox(width: 8),
                                              ],
                                              if (pace != null)
                                                _Chip(Icons.speed, '${_paceStr(pace)} /km'),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                    const Icon(Icons.chevron_right, color: Color(0xFF334155)),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
      );

  String _paceStr(dynamic secPerKm) {
    final s = (secPerKm as num).toInt();
    final m = s ~/ 60;
    final sec = s % 60;
    return '$m:${sec.toString().padLeft(2, '0')}';
  }
}

class _FriendAvatar extends StatelessWidget {
  final String? avatarUrl;
  final String name;
  final double radius;
  const _FriendAvatar({this.avatarUrl, required this.name, this.radius = 17});

  @override
  Widget build(BuildContext context) {
    final fallback = CircleAvatar(
      radius: radius,
      backgroundColor: const Color(0xFF6366f1).withOpacity(0.2),
      child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?',
          style: const TextStyle(color: Color(0xFF6366f1), fontWeight: FontWeight.bold, fontSize: 13)),
    );
    if (avatarUrl == null) return fallback;
    return FutureBuilder<String?>(
      future: ApiService().getAuthHeader(),
      builder: (context, snap) {
        if (!snap.hasData || snap.data == null) return fallback;
        final url = '${ApiService.baseUrl.replaceAll('/api/v1', '')}$avatarUrl';
        return ClipOval(
          child: Image.network(url, width: radius * 2, height: radius * 2, fit: BoxFit.cover,
              headers: {'Authorization': snap.data!},
              errorBuilder: (_, __, ___) => fallback),
        );
      },
    );
  }
}

class _Chip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _Chip(this.icon, this.label);

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: const Color(0xFF64748b)),
          const SizedBox(width: 3),
          Text(label, style: const TextStyle(color: Color(0xFF64748b), fontSize: 11)),
        ],
      );
}
