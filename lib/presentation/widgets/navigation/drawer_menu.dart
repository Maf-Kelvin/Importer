// lib/presentation/widgets/navigation/drawer_menu.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../routes/route_names.dart';

class DrawerMenu extends ConsumerWidget {
  const DrawerMenu({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    final authNotifier = ref.read(authProvider.notifier);

    return Drawer(
      child: Column(
        children: [
          // Header
          DrawerHeader(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primary,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 24.r,
                  backgroundColor: Colors.white,
                  child: Icon(
                    Icons.person,
                    size: 32.w,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                ),
                SizedBox(height: 12.h),
                Text(
                  currentUser?.fullName ?? 'User',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                Text(
                  currentUser?.email ?? '',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withOpacity(0.8),
                      ),
                ),
                SizedBox(height: 8.h),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                  child: Text(
                    currentUser?.role.toUpperCase() ?? '',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                ),
              ],
            ),
          ),

          // Menu items
          Expanded(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                ListTile(
                  leading: const Icon(Icons.person_outline),
                  title: const Text('Profile'),
                  onTap: () {
                    Navigator.pop(context);
                    context.go(RouteNames.profile);
                  },
                ),
                
                if (currentUser?.isManagerOrAbove == true)
                  ListTile(
                    leading: const Icon(Icons.local_shipping_outlined),
                    title: const Text('Tracking'),
                    onTap: () {
                      Navigator.pop(context);
                      // Navigate to tracking screen
                    },
                  ),

                if (currentUser?.isAdmin == true)
                  ListTile(
                    leading: const Icon(Icons.people_outline),
                    title: const Text('User Management'),
                    onTap: () {
                      Navigator.pop(context);
                      // Navigate to user management
                    },
                  ),

                ListTile(
                  leading: const Icon(Icons.upload_file_outlined),
                  title: const Text('Export Data'),
                  onTap: () {
                    Navigator.pop(context);
                    // Handle export
                  },
                ),

                const Divider(),

                ListTile(
                  leading: const Icon(Icons.help_outline),
                  title: const Text('Help & Support'),
                  onTap: () {
                    Navigator.pop(context);
                    // Navigate to help
                  },
                ),

                ListTile(
                  leading: const Icon(Icons.info_outline),
                  title: const Text('About'),
                  onTap: () {
                    Navigator.pop(context);
                    // Show about dialog
                    _showAboutDialog(context);
                  },
                ),
              ],
            ),
          ),

          // Logout
          const Divider(),
          ListTile(
            leading: Icon(
              Icons.logout,
              color: Theme.of(context).colorScheme.error,
            ),
            title: Text(
              'Logout',
              style: TextStyle(
                color: Theme.of(context).colorScheme.error,
              ),
            ),
            onTap: () async {
              Navigator.pop(context);
              await authNotifier.logout();
            },
          ),
          SizedBox(height: 16.h),
        ],
      ),
    );
  }

  void _showAboutDialog(BuildContext context) {
    showAboutDialog(
      context: context,
      applicationName: 'Import Logistics',
      applicationVersion: '1.0.0',
      applicationIcon: Icon(
        Icons.inventory_2_outlined,
        size: 48.w,
      ),
      children: [
        const Text('Import Profit & Logistics Intelligence System'),
        const Text('Manage containers, track shipments, and optimize profits.'),
      ],
    );
  }
}