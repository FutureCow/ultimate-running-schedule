import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';

class FriendsScreen extends StatefulWidget {
  const FriendsScreen({super.key});
  @override
  State<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends State<FriendsScreen> with SingleTickerProviderStateMixin {
  late final TabController _tab;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('Vrienden'),
          bottom: TabBar(
            controller: _tab,
            tabs: const [
              Tab(text: 'Mijn vrienden'),
              Tab(text: 'Zoeken & verzoeken'),
            ],
          ),
        ),
        body: TabBarView(
          controller: _tab,
          children: const [
            _FriendListTab(),
            _SearchTab(),
          ],
        ),
      );
}

// ── Search + pending requests ─────────────────────────────────────────────────

class _SearchTab extends StatefulWidget {
  const _SearchTab();
  @override
  State<_SearchTab> createState() => _SearchTabState();
}

class _SearchTabState extends State<_SearchTab> {
  final _api = ApiService();
  final _nameCtrl = TextEditingController();
  List<Map<String, dynamic>> _results = [];
  List<Map<String, dynamic>> _requests = [];
  bool _searching = false;
  bool _loadingRequests = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadRequests();
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadRequests() async {
    setState(() => _loadingRequests = true);
    try {
      final res = await _api.getFriendRequests();
      setState(() => _requests = List<Map<String, dynamic>>.from(res.data['requests'] ?? []));
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loadingRequests = false);
    }
  }

  Future<void> _search() async {
    final name = _nameCtrl.text.trim();
    if (name.length < 2) return;
    setState(() { _searching = true; _error = ''; _results = []; });
    try {
      final res = await _api.searchFriends(name);
      setState(() => _results = List<Map<String, dynamic>>.from(res.data['users'] ?? []));
    } catch (_) {
      setState(() => _error = 'Zoeken mislukt. Probeer opnieuw.');
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _sendRequest(int userId) async {
    try {
      await _api.sendFriendRequest(userId);
      _search();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Verzoek sturen mislukt.')),
        );
      }
    }
  }

  Future<void> _acceptRequest(int friendshipId) async {
    try {
      await _api.acceptFriendRequest(friendshipId);
      _loadRequests();
    } catch (_) {}
  }

  Future<void> _declineRequest(int friendshipId) async {
    try {
      await _api.declineFriendRequest(friendshipId);
      _loadRequests();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Search bar
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _nameCtrl,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Voor- en achternaam',
                    hintStyle: const TextStyle(color: Color(0xFF64748b)),
                    filled: true,
                    fillColor: const Color(0xFF1e293b),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  ),
                  onSubmitted: (_) => _search(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _searching ? null : _search,
                child: _searching
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.search),
              ),
            ],
          ),
          if (_error.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(_error, style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
          ],
          if (_results.isNotEmpty) ...[
            const SizedBox(height: 16),
            ..._results.map((u) {
              final status = u['friendship_status'] as String? ?? 'none';
              return _UserTile(
                name: u['name'] ?? '',
                avatarUrl: u['avatar_url'],
                trailing: _statusWidget(u['id'] as int, status),
              );
            }),
          ],

          // Pending requests
          const SizedBox(height: 24),
          const Text('Openstaande verzoeken',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
          const SizedBox(height: 10),
          if (_loadingRequests)
            const Center(child: CircularProgressIndicator())
          else if (_requests.isEmpty)
            const Text('Geen openstaande verzoeken.',
                style: TextStyle(color: Color(0xFF64748b), fontSize: 13))
          else
            ..._requests.map((r) => _UserTile(
                  name: (r['user'] as Map<String, dynamic>?)?['name'] ?? '',
                  avatarUrl: (r['user'] as Map<String, dynamic>?)?['avatar_url'],
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.check_circle_outline, color: Colors.green),
                        onPressed: () => _acceptRequest(r['friendship_id'] as int),
                        tooltip: 'Accepteren',
                      ),
                      IconButton(
                        icon: const Icon(Icons.cancel_outlined, color: Colors.red),
                        onPressed: () => _declineRequest(r['friendship_id'] as int),
                        tooltip: 'Weigeren',
                      ),
                    ],
                  ),
                )),
        ],
      );

  Widget _statusWidget(int userId, String status) {
    if (status == 'accepted') {
      return const Chip(
        label: Text('Vrienden', style: TextStyle(fontSize: 11)),
        backgroundColor: Color(0xFF166534),
      );
    }
    if (status == 'pending') {
      return const Chip(
        label: Text('Verstuurd', style: TextStyle(fontSize: 11)),
        backgroundColor: Color(0xFF1e293b),
      );
    }
    if (status.startsWith('incoming_')) {
      return const Chip(
        label: Text('Ontvangen', style: TextStyle(fontSize: 11, color: Colors.amber)),
        backgroundColor: Color(0xFF1e293b),
      );
    }
    return TextButton.icon(
      onPressed: () => _sendRequest(userId),
      icon: const Icon(Icons.person_add_outlined, size: 16),
      label: const Text('Verzoek sturen'),
    );
  }
}

// ── Friends list ──────────────────────────────────────────────────────────────

class _FriendListTab extends StatefulWidget {
  const _FriendListTab();
  @override
  State<_FriendListTab> createState() => _FriendListTabState();
}

class _FriendListTabState extends State<_FriendListTab> {
  final _api = ApiService();
  List<Map<String, dynamic>> _friends = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await _api.getFriends();
      setState(() => _friends = List<Map<String, dynamic>>.from(res.data['friends'] ?? []));
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _remove(int friendId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Vriend verwijderen?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuleren')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Verwijderen')),
        ],
      ),
    );
    if (ok == true) {
      try {
        await _api.removeFriend(friendId);
        _load();
      } catch (_) {}
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_friends.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.group_outlined, size: 64, color: Color(0xFF334155)),
            const SizedBox(height: 16),
            const Text('Nog geen vrienden', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text('Zoek vrienden via het zoektabblad', style: TextStyle(color: Colors.grey[500])),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _friends.length,
        itemBuilder: (_, i) {
          final f = _friends[i];
          final user = f['user'] as Map<String, dynamic>? ?? {};
          return _UserTile(
            name: user['name'] ?? '',
            avatarUrl: user['avatar_url'],
            onTap: () => context.push('/friends/${user['id']}'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.chevron_right, color: Color(0xFF6366f1)),
                IconButton(
                  icon: const Icon(Icons.person_remove_outlined, size: 20, color: Color(0xFF64748b)),
                  onPressed: () => _remove(user['id'] as int),
                  tooltip: 'Verwijderen',
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ── Shared widgets ────────────────────────────────────────────────────────────

class _UserTile extends StatelessWidget {
  final String name;
  final String? avatarUrl;
  final Widget? trailing;
  final VoidCallback? onTap;

  const _UserTile({required this.name, this.avatarUrl, this.trailing, this.onTap});

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF1e293b),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: const Color(0xFF6366f1).withOpacity(0.2),
                backgroundImage: avatarUrl != null ? NetworkImage(avatarUrl!) : null,
                child: avatarUrl == null
                    ? Text(name.isNotEmpty ? name[0].toUpperCase() : '?',
                        style: const TextStyle(color: Color(0xFF6366f1), fontWeight: FontWeight.bold))
                    : null,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(name,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 14),
                    maxLines: 1, overflow: TextOverflow.ellipsis),
              ),
              if (trailing != null) trailing!,
            ],
          ),
        ),
      );
}
