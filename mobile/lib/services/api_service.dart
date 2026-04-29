import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/app_config.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late final Dio _dio;
  final _storage = const FlutterSecureStorage();
  bool _refreshing = false;

  ApiService._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      },
      onError: (err, handler) async {
        if (err.response?.statusCode == 401 && !_refreshing) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            final token = await _storage.read(key: 'access_token');
            err.requestOptions.headers['Authorization'] = 'Bearer $token';
            final retry = await _dio.fetch(err.requestOptions);
            return handler.resolve(retry);
          }
        }
        handler.next(err);
      },
    ));
  }

  Future<bool> _tryRefresh() async {
    _refreshing = true;
    try {
      final refresh = await _storage.read(key: 'refresh_token');
      if (refresh == null) return false;
      final res = await _dio.post('/auth/refresh',
          data: {'refresh_token': refresh},
          options: Options(headers: {}));
      await _storage.write(key: 'access_token', value: res.data['access_token']);
      if (res.data['refresh_token'] != null) {
        await _storage.write(key: 'refresh_token', value: res.data['refresh_token']);
      }
      return true;
    } catch (_) {
      await clearTokens();
      return false;
    } finally {
      _refreshing = false;
    }
  }

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.deleteAll();
  }

  Future<bool> hasToken() async {
    final t = await _storage.read(key: 'access_token');
    return t != null;
  }

  // Auth
  Future<Response> login(String email, String password) =>
      _dio.post('/auth/login', data: {'email': email, 'password': password});

  Future<Response> register(String email, String password, String name) =>
      _dio.post('/auth/register', data: {'email': email, 'password': password, 'name': name});

  Future<Response> getMe() => _dio.get('/auth/profile');
  Future<Response> updateProfile(Map<String, dynamic> data) =>
      _dio.patch('/auth/profile', data: data);

  // Plans
  Future<Response> getPlans() => _dio.get('/plans');
  Future<Response> getPlan(String publicId) => _dio.get('/plans/$publicId');

  // Sessions
  Future<Response> getSessions(int planId) => _dio.get('/sessions', queryParameters: {'plan_id': planId});
  Future<Response> markComplete(int sessionId) => _dio.post('/sessions/$sessionId/complete');

  // Garmin / Activities
  Future<Response> getActivities() => _dio.get('/garmin/activities');
  Future<Response> getActivity(String id) => _dio.get('/garmin/activity/$id');
  Future<Response> syncGarmin() => _dio.post('/garmin/sync');
}
