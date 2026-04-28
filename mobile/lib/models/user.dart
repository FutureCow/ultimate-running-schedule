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
        id: j['id'],
        email: j['email'],
        name: j['name'] ?? '',
        tier: j['tier'] ?? 'free',
        weeklyKm: (j['weekly_km'] as num?)?.toDouble(),
      );
}
