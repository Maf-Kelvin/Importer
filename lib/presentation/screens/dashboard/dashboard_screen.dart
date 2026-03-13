// lib/presentation/screens/dashboard/dashboard_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../widgets/navigation/bottom_nav_bar.dart';
import '../../widgets/navigation/drawer_menu.dart';
import '../../routes/route_names.dart';
import '../dashboard/widgets/metric_card.dart';
import '../dashboard/widgets/recent_activity.dart';
import '../../../core/utils/responsive.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Welcome, ${currentUser?.firstName ?? 'User'}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              // Handle notifications
            },
          ),
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {
              // Handle search
            },
          ),
        ],
      ),
      drawer: Responsive.isMobile(context) ? const DrawerMenu() : null,
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Quick actions
              _buildQuickActions(context),
              SizedBox(height: 24.h),

              // Metrics overview
              _buildMetricsSection(),
              SizedBox(height: 24.h),

              // Recent activity
              _buildRecentActivity(),
            ],
          ),
        ),
      ),
      bottomNavigationBar: Responsive.isMobile(context)
          ? const BottomNavBar(currentIndex: 0)
          : null,
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go(RouteNames.createContainer),
        child: const Icon(Icons.add),
      ),
    );
  }

  Future<void> _handleRefresh() async {
    // Implement refresh logic
    await Future.delayed(const Duration(seconds: 1));
  }

  Widget _buildQuickActions(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Quick Actions',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        SizedBox(height: 12.h),
        Row(
          children: [
            Expanded(
              child: _QuickActionCard(
                icon: Icons.inventory_2_outlined,
                title: 'New Container',
                subtitle: 'Create container',
                onTap: () => context.go('/containers/create'),
              ),
            ),
            SizedBox(width: 12.w),
            Expanded(
              child: _QuickActionCard(
                icon: Icons.add_box_outlined,
                title: 'Add Item',
                subtitle: 'Add to container',
                onTap: () => context.go('/items/create'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildMetricsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Overview',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        SizedBox(height: 12.h),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: Responsive.gridColumns(context),
          childAspectRatio: 1.5,
          crossAxisSpacing: 12.w,
          mainAxisSpacing: 12.h,
          children: const [
            MetricCard(
              title: 'Active Containers',
              value: '12',
              icon: Icons.inventory_2,
              color: Colors.blue,
              subtitle: '3 new this month',
            ),
            MetricCard(
              title: 'Total Items',
              value: '348',
              icon: Icons.category,
              color: Colors.green,
              subtitle: '45 sold this week',
            ),
            MetricCard(
              title: 'Revenue',
              value: '\$24,500',
              icon: Icons.attach_money,
              color: Colors.orange,
              subtitle: '+12% from last month',
            ),
            MetricCard(
              title: 'Profit Margin',
              value: '28.5%',
              icon: Icons.trending_up,
              color: Colors.purple,
              subtitle: 'Above target',
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRecentActivity() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Recent Activity',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            TextButton(
              onPressed: () => context.go(RouteNames.containers),
              child: const Text('View All'),
            ),
          ],
        ),
        SizedBox(height: 12.h),
        const RecentActivity(),
      ],
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12.r),
        child: Padding(
          padding: EdgeInsets.all(16.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                icon,
                size: 32.w,
                color: Theme.of(context).colorScheme.primary,
              ),
              SizedBox(height: 8.h),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
