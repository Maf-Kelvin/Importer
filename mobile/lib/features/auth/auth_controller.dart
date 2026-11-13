import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'user.dart';

/// The signed-in user, or null when signed out. While it loads, the app shows a splash screen.
class AuthController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final tokens = ref.read(tokenStoreProvider);
    if (await tokens.readAccess() == null && await tokens.readRefresh() == null) return null;
    try {
      return await _fetchMe();
    } on DioException catch (e) {
      // 401 after a failed refresh means the session is over. A network error should not sign
      // the person out, but with no user loaded the safest screen is login.
      if (e.response?.statusCode == 401) await tokens.clear();
      return null;
    }
  }

  Future<AppUser> _fetchMe() async {
    final r = await ref.read(apiClientProvider).dio.get<Map<String, dynamic>>('/users/me');
    return AppUser.fromJson(r.data!);
  }

  /// Throws a DioException (or other error) on failure; the login screen shows friendlyError().
  Future<void> login(String username, String password) async {
    final api = ref.read(apiClientProvider);
    final r = await api.bare.post<Map<String, dynamic>>(
      '/auth/login',
      data: {'username': username.trim(), 'password': password},
      options: Options(contentType: Headers.formUrlEncodedContentType),
    );
    final data = r.data!;
    await ref.read(tokenStoreProvider).save(
          access: data['access_token'] as String,
          refresh: data['refresh_token'] as String?,
        );
    state = AsyncData(await _fetchMe());
  }

  Future<void> logout() async {
    final tokens = ref.read(tokenStoreProvider);
    final refresh = await tokens.readRefresh();
    try {
      await ref.read(apiClientProvider).dio.post<dynamic>(
            '/auth/logout',
            data: refresh == null ? null : {'refresh_token': refresh},
          );
    } catch (_) {
      // Signing out locally must work even when the server cannot be reached.
    }
    await tokens.clear();
    state = const AsyncData(null);
  }

  /// Called by the API client when a refresh fails.
  Future<void> sessionExpired() async {
    await ref.read(tokenStoreProvider).clear();
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthController, AppUser?>(AuthController.new);
