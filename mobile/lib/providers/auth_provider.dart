import 'package:flutter/foundation.dart';
import '../models/user.dart';
import '../services/api_service.dart';

enum AuthState { unknown, authenticated, unauthenticated }

class AuthProvider extends ChangeNotifier {
  final _api = ApiService();

  AuthState _state = AuthState.unknown;
  User? _user;
  String? _error;

  AuthState get state => _state;
  User? get user => _user;
  String? get error => _error;
  bool get isLoading => _state == AuthState.unknown;

  Future<void> init() async {
    if (await _api.hasToken()) {
      await _loadUser();
    } else {
      _state = AuthState.unauthenticated;
      notifyListeners();
    }
  }

  Future<void> _loadUser() async {
    try {
      final res = await _api.getMe();
      _user = User.fromJson(res.data as Map<String, dynamic>);
      _state = AuthState.authenticated;
    } catch (e) {
      _state = AuthState.unauthenticated;
      _error = 'Kon gebruikersgegevens niet ophalen: ${e.toString().split('\n').first}';
    }
    notifyListeners();
  }

  Future<bool> login(String email, String password) async {
    _error = null;
    try {
      final res = await _api.login(email, password);
      await _api.saveTokens(res.data['access_token'], res.data['refresh_token']);
      await _loadUser();
      return true;
    } catch (e) {
      _error = _parseError(e);
      notifyListeners();
      return false;
    }
  }

  Future<bool> register(String email, String password, String name) async {
    _error = null;
    try {
      final res = await _api.register(email, password, name);
      await _api.saveTokens(res.data['access_token'], res.data['refresh_token']);
      await _loadUser();
      return true;
    } catch (e) {
      _error = _parseError(e);
      notifyListeners();
      return false;
    }
  }

  Future<void> reloadUser() async => _loadUser();

  Future<void> logout() async {
    await _api.clearTokens();
    _user = null;
    _state = AuthState.unauthenticated;
    notifyListeners();
  }

  String _parseError(dynamic e) {
    if (e is Exception) {
      final msg = e.toString();
      if (msg.contains('401') || msg.contains('Incorrect')) return 'Onjuist e-mailadres of wachtwoord';
      if (msg.contains('422')) return 'Controleer je invoer';
      if (msg.contains('Connection')) return 'Kan geen verbinding maken met de server';
    }
    return 'Er is een fout opgetreden';
  }
}
