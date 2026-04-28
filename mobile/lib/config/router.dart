import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/plan/plan_screen.dart';
import '../screens/analyse/analyse_screen.dart';
import '../screens/analyse/activity_detail_screen.dart';
import '../screens/settings/settings_screen.dart';

final _rootKey = GlobalKey<NavigatorState>();
final _shellKey = GlobalKey<NavigatorState>();

GoRouter buildRouter(AuthProvider auth) => GoRouter(
      navigatorKey: _rootKey,
      refreshListenable: auth,
      redirect: (context, state) {
        final loggedIn = auth.state == AuthState.authenticated;
        final loading = auth.state == AuthState.unknown;
        if (loading) return null;
        final onAuth = state.matchedLocation == '/login' ||
            state.matchedLocation == '/register';
        if (!loggedIn && !onAuth) return '/login';
        if (loggedIn && onAuth) return '/dashboard';
        return null;
      },
      routes: [
        GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
        GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
        ShellRoute(
          navigatorKey: _shellKey,
          builder: (_, state, child) => _Shell(child: child, location: state.matchedLocation),
          routes: [
            GoRoute(
              path: '/dashboard',
              builder: (_, __) => const DashboardScreen(),
            ),
            GoRoute(
              path: '/plan',
              builder: (_, __) => const PlanScreen(),
            ),
            GoRoute(
              path: '/analyse',
              builder: (_, __) => const AnalyseScreen(),
              routes: [
                GoRoute(
                  path: ':activityId',
                  parentNavigatorKey: _rootKey,
                  builder: (_, state) => ActivityDetailScreen(
                    activityId: state.pathParameters['activityId']!,
                  ),
                ),
              ],
            ),
            GoRoute(
              path: '/settings',
              builder: (_, __) => const SettingsScreen(),
            ),
          ],
        ),
      ],
      initialLocation: '/dashboard',
    );

class _Shell extends StatelessWidget {
  final Widget child;
  final String location;
  const _Shell({required this.child, required this.location});

  int get _index {
    if (location.startsWith('/dashboard')) return 0;
    if (location.startsWith('/plan')) return 1;
    if (location.startsWith('/analyse')) return 2;
    if (location.startsWith('/settings')) return 3;
    return 0;
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: child,
        bottomNavigationBar: BottomNavigationBar(
          currentIndex: _index,
          onTap: (i) {
            const routes = ['/dashboard', '/plan', '/analyse', '/settings'];
            context.go(routes[i]);
          },
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.home_outlined), activeIcon: Icon(Icons.home), label: 'Dashboard'),
            BottomNavigationBarItem(icon: Icon(Icons.calendar_month_outlined), activeIcon: Icon(Icons.calendar_month), label: 'Plan'),
            BottomNavigationBarItem(icon: Icon(Icons.bar_chart_outlined), activeIcon: Icon(Icons.bar_chart), label: 'Analyse'),
            BottomNavigationBarItem(icon: Icon(Icons.settings_outlined), activeIcon: Icon(Icons.settings), label: 'Instellingen'),
          ],
        ),
      );
}
