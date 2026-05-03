import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../config/app_config.dart';

class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  static String get baseUrl => AppConfig.apiBaseUrl;

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
        if (options.data is FormData) {
          options.headers.remove('Content-Type');
        }
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
    } on DioException catch (e) {
      // Only wipe tokens when the server explicitly rejects the refresh token.
      // Network errors, timeouts, etc. are transient — keep tokens so the user
      // stays logged in and the next request will retry the refresh.
      if (e.response?.statusCode == 401) {
        await clearTokens();
      }
      return false;
    } catch (_) {
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

  Future<Response> resetSession(int sessionId) => _dio.post('/sessions/$sessionId/reset');

  Future<Response> getMe() => _dio.get('/auth/profile');
  Future<Response> updateProfile(Map<String, dynamic> data) =>
      _dio.patch('/auth/profile', data: data);
  Future<Response> uploadAvatar(String filePath) {
    final ext = filePath.split('.').last.toLowerCase();
    final contentType = ext == 'png'
        ? DioMediaType('image', 'png')
        : ext == 'webp'
            ? DioMediaType('image', 'webp')
            : DioMediaType('image', 'jpeg');
    final form = FormData.fromMap({
      'file': MultipartFile.fromFileSync(filePath,
          filename: filePath.split('/').last,
          contentType: contentType),
    });
    return _dio.post('/auth/profile/avatar', data: form);
  }

  // Plans
  Future<Response> getPlans() => _dio.get('/plans');
  Future<Response> getPlan(String publicId) => _dio.get('/plans/$publicId');
  Future<Response> bulkEditSessions(String publicId, Map<String, dynamic> filter, Map<String, dynamic> update) =>
      _dio.patch('/plans/$publicId/sessions/bulk', data: {'filter': filter, 'update': update});

  // Sessions
  Future<Response> getSessions(int planId) => _dio.get('/sessions', queryParameters: {'plan_id': planId});
  Future<Response> markComplete(int sessionId) => _dio.post('/sessions/$sessionId/complete');
  Future<Response> updateSessionDetails(int sessionId, Map<String, dynamic> data) =>
      _dio.patch('/sessions/$sessionId/details', data: data);

  // Garmin / Activities
  Future<Response> getActivities() => _dio.get('/garmin/activities');
  Future<Response> getActivity(String id) => _dio.get('/garmin/activity/$id');
  Future<Response> syncGarmin() => _dio.post('/garmin/sync');
  Future<Response> previewRegeneratePlan(String publicId) =>
      _dio.post('/plans/$publicId/regenerate/preview');
  Future<Response> resetPlan(String publicId) =>
      _dio.post('/plans/$publicId/reset');
  Future<Response> regeneratePlan(String publicId) =>
      _dio.post('/plans/$publicId/regenerate');
  Future<Response> pushSessions(List<int> sessionIds) =>
      _dio.post('/garmin/push/sessions', data: {'session_ids': sessionIds});
  Future<Response> pushWeek(String publicId, int weekNumber) =>
      _dio.post('/garmin/push/week', data: {'plan_id': publicId, 'week_number': weekNumber});
  Future<Response> removeGarminSession(int sessionId) =>
      _dio.delete('/garmin/sessions/$sessionId');

  // Friends
  Future<Response> searchFriends(String name) =>
      _dio.post('/friends/search', data: {'name': name});
  Future<Response> sendFriendRequest(int addresseeId) =>
      _dio.post('/friends/request/$addresseeId');
  Future<Response> getFriendRequests() => _dio.get('/friends/requests');
  Future<Response> getSentRequests() => _dio.get('/friends/sent');
  Future<Response> acceptFriendRequest(int friendshipId) =>
      _dio.post('/friends/requests/$friendshipId/accept');
  Future<Response> declineFriendRequest(int friendshipId) =>
      _dio.delete('/friends/requests/$friendshipId');
  Future<Response> getFriends() => _dio.get('/friends');
  Future<Response> removeFriend(int friendId) =>
      _dio.delete('/friends/$friendId');
  Future<Response> getFriendActivities(int friendId) =>
      _dio.get('/friends/$friendId/activities');
  Future<Response> getFriendActivity(int friendId, String activityId) =>
      _dio.get('/friends/$friendId/activity/$activityId');
}
