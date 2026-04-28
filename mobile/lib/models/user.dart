class User {
  final int id;
  final String email;
  final String name;
  final String tier;
  final double? weeklyKm;

  const User({
    required this.id,
    required this.email,
    required this.name,
    required this.tier,
    this.weeklyKm,
  });

  factory User.fromJson(Map<String, dynamic> j) => User(
        id: (j['id'] as num?)?.toInt() ?? 0,
        email: j['email'] as String? ?? '',
        name: j['name'] as String? ?? (j['email'] as String? ?? '').split('@').first,
        tier: j['tier'] as String? ?? 'free',
        weeklyKm: (j['weekly_km'] as num?)?.toDouble(),
      );
}
