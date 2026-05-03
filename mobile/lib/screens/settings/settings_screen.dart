import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _api = ApiService();
  final _nameCtrl = TextEditingController();
  final _ageCtrl = TextEditingController();
  final _maxHrCtrl = TextEditingController();
  final _weeklyKmCtrl = TextEditingController();
  bool _saving = false;
  String? _saveError;
  bool _saved = false;
  bool _uploadingAvatar = false;
  String? _avatarError;

  @override
  void initState() {
    super.initState();
    final user = context.read<AuthProvider>().user;
    if (user != null) {
      _nameCtrl.text = user.name;
      _ageCtrl.text = user.age?.toString() ?? '';
      _maxHrCtrl.text = user.maxHr?.toString() ?? '';
      _weeklyKmCtrl.text = user.weeklyKm?.toStringAsFixed(0) ?? '';
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _maxHrCtrl.dispose();
    _weeklyKmCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickAndUploadAvatar() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85, maxWidth: 512);
    if (picked == null) return;
    setState(() { _uploadingAvatar = true; _avatarError = null; });
    try {
      await _api.uploadAvatar(picked.path);
      await context.read<AuthProvider>().reloadUser();
    } catch (e) {
      if (mounted) setState(() => _avatarError = 'Upload mislukt');
    } finally {
      if (mounted) setState(() => _uploadingAvatar = false);
    }
  }

  Future<void> _save() async {
    setState(() { _saving = true; _saveError = null; _saved = false; });
    try {
      await _api.updateProfile({
        'name': _nameCtrl.text,
        if (_ageCtrl.text.isNotEmpty) 'age': int.parse(_ageCtrl.text),
        if (_maxHrCtrl.text.isNotEmpty) 'max_hr': int.parse(_maxHrCtrl.text),
        if (_weeklyKmCtrl.text.isNotEmpty) 'weekly_km': double.parse(_weeklyKmCtrl.text),
      });
      await context.read<AuthProvider>().reloadUser();
      if (mounted) setState(() => _saved = true);
    } catch (e) {
      if (mounted) setState(() => _saveError = 'Opslaan mislukt: ${e.toString().split('\n').first}');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Widget _buildAvatar(user) {
    if (user?.avatarUrl != null) {
      return FutureBuilder<String?>(
        future: ApiService().getAuthHeader(),
        builder: (context, snap) {
          final headers = snap.hasData && snap.data != null
              ? {'Authorization': snap.data!} : <String, String>{};
          final url = '${ApiService.baseUrl.replaceAll('/api/v1', '')}${user!.avatarUrl}';
          return ClipOval(
            child: Image.network(url, width: 56, height: 56, fit: BoxFit.cover,
                headers: headers,
                errorBuilder: (_, __, ___) => _avatarFallback(user)),
          );
        },
      );
    }
    return _avatarFallback(user);
  }

  Widget _avatarFallback(user) => CircleAvatar(
        radius: 28,
        backgroundColor: const Color(0xFF6366f1).withOpacity(0.2),
        child: Text(
          (user?.name.isNotEmpty == true ? user!.name[0] : '?').toUpperCase(),
          style: const TextStyle(color: Color(0xFF6366f1), fontSize: 22, fontWeight: FontWeight.bold),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().user;
    return Scaffold(
      appBar: AppBar(title: const Text('Instellingen')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Profile card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1e293b),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(children: [
              GestureDetector(
                onTap: _pickAndUploadAvatar,
                child: Stack(
                  children: [
                    _buildAvatar(user),
                    Positioned(
                      bottom: 0, right: 0,
                      child: Container(
                        width: 22, height: 22,
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366f1),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFF1e293b), width: 2),
                        ),
                        child: _uploadingAvatar
                            ? const Padding(
                                padding: EdgeInsets.all(4),
                                child: CircularProgressIndicator(strokeWidth: 1.5, color: Colors.white),
                              )
                            : const Icon(Icons.camera_alt, size: 12, color: Colors.white),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(user?.email ?? '–',
                      style: const TextStyle(color: Color(0xFF64748b), fontSize: 12)),
                  const SizedBox(height: 2),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366f1).withOpacity(0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      (user?.tier ?? 'free').toUpperCase(),
                      style: const TextStyle(color: Color(0xFF6366f1), fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              )),
            ]),
          ),
          if (_avatarError != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_avatarError!, style: const TextStyle(color: Colors.red, fontSize: 12)),
            ),

          const SizedBox(height: 24),
          const _SectionHeader('Profiel'),
          _ProfileField(
            label: 'Naam',
            hint: 'bijv. Jan de Vries',
            controller: _nameCtrl,
            suffix: '',
            keyboardType: TextInputType.name,
          ),
          const SizedBox(height: 12),
          const _SectionHeader('Atletenprofiel'),

          _ProfileField(
            label: 'Leeftijd',
            hint: 'bijv. 35',
            controller: _ageCtrl,
            suffix: 'jaar',
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          _ProfileField(
            label: 'Max hartslag',
            hint: 'bijv. 185',
            controller: _maxHrCtrl,
            suffix: 'bpm',
            keyboardType: TextInputType.number,
            helperText: 'Gebruik je gemeten max-HR voor nauwkeurige hartslagzones in de AI-analyse.',
          ),
          const SizedBox(height: 12),
          _ProfileField(
            label: 'Weekkilometers',
            hint: 'bijv. 50',
            controller: _weeklyKmCtrl,
            suffix: 'km',
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
          ),

          const SizedBox(height: 20),

          if (_saveError != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(_saveError!, style: const TextStyle(color: Colors.red, fontSize: 13)),
            ),
          if (_saved)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: Row(children: [
                Icon(Icons.check_circle, color: Color(0xFF22c55e), size: 16),
                SizedBox(width: 6),
                Text('Opgeslagen', style: TextStyle(color: Color(0xFF22c55e), fontSize: 13)),
              ]),
            ),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: _saving ? null : _save,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366f1),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: _saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Opslaan'),
            ),
          ),

          const SizedBox(height: 24),
          const _SectionHeader('Garmin'),
          _SettingsTile(
            icon: Icons.sync,
            title: 'Activiteiten synchroniseren',
            onTap: () => context.go('/analyse'),
          ),

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () async {
                await context.read<AuthProvider>().logout();
                if (context.mounted) context.go('/login');
              },
              icon: const Icon(Icons.logout, color: Colors.red),
              label: const Text('Uitloggen', style: TextStyle(color: Colors.red)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.red),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(title,
            style: const TextStyle(color: Color(0xFF64748b), fontSize: 12,
                fontWeight: FontWeight.w600, letterSpacing: 0.5)),
      );
}

class _ProfileField extends StatelessWidget {
  final String label;
  final String hint;
  final TextEditingController controller;
  final String suffix;
  final TextInputType keyboardType;
  final String? helperText;

  const _ProfileField({
    required this.label,
    required this.hint,
    required this.controller,
    required this.suffix,
    required this.keyboardType,
    this.helperText,
  });

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Color(0xFF94a3b8), fontSize: 12, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          TextField(
            controller: controller,
            keyboardType: keyboardType,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: const TextStyle(color: Color(0xFF475569)),
              suffixText: suffix,
              suffixStyle: const TextStyle(color: Color(0xFF64748b)),
              filled: true,
              fillColor: const Color(0xFF1e293b),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Color(0xFF334155)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Color(0xFF334155)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: Color(0xFF6366f1)),
              ),
            ),
          ),
          if (helperText != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(helperText!, style: const TextStyle(color: Color(0xFF475569), fontSize: 11)),
            ),
        ],
      );
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _SettingsTile({required this.icon, required this.title, required this.onTap});

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(color: const Color(0xFF1e293b), borderRadius: BorderRadius.circular(12)),
        child: ListTile(
          leading: Icon(icon, color: const Color(0xFF64748b), size: 20),
          title: Text(title, style: const TextStyle(color: Colors.white, fontSize: 14)),
          trailing: const Icon(Icons.chevron_right, color: Color(0xFF334155), size: 18),
          onTap: onTap,
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      );
}
