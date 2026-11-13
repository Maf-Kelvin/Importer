import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/containers/container_detail_screen.dart';
import 'features/containers/models.dart';
import 'features/containers/containers_screen.dart';
import 'features/customers/add_customer_screen.dart';
import 'features/customers/customers_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/items/add_item_screen.dart';
import 'features/items/items_screen.dart';
import 'features/media/item_media_screen.dart';
import 'features/reports/reports_screen.dart';
import 'features/settings/settings_screen.dart';
import 'shell/app_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.listen(authProvider, (_, __) => refresh.value++);
  ref.onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final at = state.matchedLocation;
      if (auth.isLoading) return at == '/splash' ? null : '/splash';
      final signedIn = auth.valueOrNull != null;
      if (!signedIn) return at == '/login' ? null : '/login';
      if (at == '/login' || at == '/splash') return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const Scaffold(body: Center(child: CircularProgressIndicator()))),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/reports', builder: (_, __) => const ReportsScreen()),
      GoRoute(
        path: '/item-edit',
        builder: (_, state) {
          final item = state.extra;
          if (item is! ItemModel) {
            return Scaffold(appBar: AppBar(title: const Text('Edit item')), body: const Center(child: Text('Open the item from its list to edit it.')));
          }
          return AddItemScreen(containerId: item.containerId, existing: item);
        },
      ),
      GoRoute(
        path: '/item-media',
        builder: (_, state) {
          final item = state.extra;
          if (item is! ItemModel) {
            return Scaffold(appBar: AppBar(title: const Text('Photos & video')), body: const Center(child: Text('Open the item from its list first.')));
          }
          return ItemMediaScreen(item: item);
        },
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => AppShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(routes: [GoRoute(path: '/', builder: (_, __) => const DashboardScreen())]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/containers',
              builder: (_, __) => const ContainersScreen(),
              routes: [
                GoRoute(
                  path: ':id',
                  builder: (_, state) => ContainerDetailScreen(containerId: int.parse(state.pathParameters['id']!)),
                  routes: [
                    GoRoute(
                      path: 'items/new',
                      builder: (_, state) => AddItemScreen(containerId: int.parse(state.pathParameters['id']!)),
                    ),
                  ],
                ),
              ],
            ),
          ]),
          StatefulShellBranch(routes: [GoRoute(path: '/items', builder: (_, __) => const ItemsScreen())]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/customers',
              builder: (_, __) => const CustomersScreen(),
              routes: [GoRoute(path: 'new', builder: (_, __) => const AddCustomerScreen())],
            ),
          ]),
          StatefulShellBranch(routes: [GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen())]),
        ],
      ),
    ],
  );
});
