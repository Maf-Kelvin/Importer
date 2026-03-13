// lib/presentation/routes/app_router.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/splash_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/containers/container_list_screen.dart';
import '../screens/containers/container_detail_screen.dart';
import '../screens/containers/create_container_screen.dart';
import '../screens/items/item_list_screen.dart';
import '../screens/items/item_detail_screen.dart';
import '../screens/items/add_item_screen.dart';
import '../screens/reports/reports_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../screens/settings/profile_screen.dart';
import 'route_names.dart';

class AppRouter {
  static final _rootNavigatorKey = GlobalKey<NavigatorState>();
  
  static GoRouter createRouter(WidgetRef ref) {
    return GoRouter(
      navigatorKey: _rootNavigatorKey,
      debugLogDiagnostics: true,
      initialLocation: RouteNames.splash,
      redirect: (context, state) {
        final authState = ref.watch(authProvider);
        final isAuthenticated = authState.status == AuthStatus.authenticated;
        final isLoading = authState.status == AuthStatus.initial;

        // Show splash while checking auth status
        if (isLoading && state.location == RouteNames.splash) {
          return null;
        }

        // Redirect to login if not authenticated
        if (!isAuthenticated && !_isAuthRoute(state.location)) {
          return RouteNames.login;
        }

        // Redirect to dashboard if authenticated and on auth routes
        if (isAuthenticated && _isAuthRoute(state.location)) {
          return RouteNames.dashboard;
        }

        return null;
      },
      routes: [
        // Splash
        GoRoute(
          path: RouteNames.splash,
          name: 'splash',
          builder: (context, state) => const SplashScreen(),
        ),

        // Auth routes
        GoRoute(
          path: RouteNames.login,
          name: 'login',
          builder: (context, state) => const LoginScreen(),
        ),

        // Main app routes
        GoRoute(
          path: RouteNames.dashboard,
          name: 'dashboard',
          builder: (context, state) => const DashboardScreen(),
        ),

        // Container routes
        GoRoute(
          path: RouteNames.containers,
          name: 'containers',
          builder: (context, state) => const ContainerListScreen(),
          routes: [
            GoRoute(
              path: 'create',
              name: 'create-container',
              builder: (context, state) => const CreateContainerScreen(),
            ),
            GoRoute(
              path: ':id',
              name: 'container-detail',
              builder: (context, state) {
                final id = int.parse(state.pathParameters['id']!);
                return ContainerDetailScreen(containerId: id);
              },
            ),
          ],
        ),

        // Item routes
        GoRoute(
          path: RouteNames.items,
          name: 'items',
          builder: (context, state) => const ItemListScreen(),
          routes: [
            GoRoute(
              path: 'create',
              name: 'add-item',
              builder: (context, state) {
                final containerId = int.tryParse(
                  state.queryParameters['containerId'] ?? '',
                );
                return AddItemScreen(containerId: containerId);
              },
            ),
            GoRoute(
              path: ':id',
              name: 'item-detail',
              builder: (context, state) {
                final id = int.parse(state.pathParameters['id']!);
                return ItemDetailScreen(itemId: id);
              },
            ),
          ],
        ),

        // Reports
        GoRoute(
          path: RouteNames.reports,
          name: 'reports',
          builder: (context, state) => const ReportsScreen(),
        ),

        // Settings
        GoRoute(
          path: RouteNames.settings,
          name: 'settings',
          builder: (context, state) => const SettingsScreen(),
        ),

        GoRoute(
          path: RouteNames.profile,
          name: 'profile',
          builder: (context, state) => const ProfileScreen(),
        ),
      ],
    );
  }

  static bool _isAuthRoute(String location) {
    return [RouteNames.splash, RouteNames.login].contains(location);
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  return AppRouter.createRouter(ref);
});