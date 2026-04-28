import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:provider/provider.dart';
import 'config/router.dart';
import 'config/theme.dart';
import 'providers/auth_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('nl', null);
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
  ));
  runApp(const UltimateRunningApp());
}

class UltimateRunningApp extends StatefulWidget {
  const UltimateRunningApp({super.key});
  @override
  State<UltimateRunningApp> createState() => _UltimateRunningAppState();
}

class _UltimateRunningAppState extends State<UltimateRunningApp> {
  late final AuthProvider _auth;

  @override
  void initState() {
    super.initState();
    _auth = AuthProvider();
    _auth.init();
  }

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider.value(
        value: _auth,
        child: Builder(
          builder: (context) {
            final router = buildRouter(context.watch<AuthProvider>());
            return MaterialApp.router(
              title: 'Ultimate Running',
              theme: AppTheme.dark,
              routerConfig: router,
              debugShowCheckedModeBanner: false,
              locale: const Locale('nl'),
            );
          },
        ),
      );
}
