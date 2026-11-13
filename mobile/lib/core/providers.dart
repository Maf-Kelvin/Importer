import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/auth/auth_controller.dart';
import 'api_client.dart';
import 'token_store.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    ref.read(tokenStoreProvider),
    // refresh failed: the session is over, so show the login screen
    onSessionExpired: () => ref.read(authProvider.notifier).sessionExpired(),
  );
});
