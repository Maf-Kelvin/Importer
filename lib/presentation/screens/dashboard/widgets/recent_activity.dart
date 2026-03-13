// lib/presentation/screens/dashboard/widgets/recent_activity.dart
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

class RecentActivity extends StatelessWidget {
  const RecentActivity({super.key});

  @override
  Widget build(BuildContext context) {
    // Mock data - replace with actual data from provider
    final activities = [
      {
        'title': 'Container CONT-2024-001 shipped',
        'subtitle': 'MSC tracking: MSCU123456',
        'time': '2 hours ago',
        'icon': Icons.local_shipping,
        'color': Colors.blue,
      },
      {
        'title': 'Samsung TV sold for \$850',
        'subtitle': 'Profit: \$250 (41.7%)',
        'time': '5 hours ago',
        'icon': Icons.sell,
        'color': Colors.green,
      },
      {
        'title': 'New container created',
        'subtitle': 'CONT-2024-002 (40ft)',
        'time': '1 day ago',
        'icon': Icons.inventory_2,
        'color': Colors.orange,
      },
      {
        'title': 'Cost allocation completed',
        'subtitle': 'CONT-2024-001 - 25 items',
        'time': '2 days ago',
        'icon': Icons.calculate,
        'color': Colors.purple,
      },
    ];

    return Card(
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: EdgeInsets.all(16.w),
        itemCount: activities.length,
        separatorBuilder: (context, index) => Divider(height: 24.h),
        itemBuilder: (context, index) {
          final activity = activities[index];
          return ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Container(
              width: 40.w,
              height: 40.w,
              decoration: BoxDecoration(
                color: (activity['color'] as Color).withOpacity(0.1),
                borderRadius: BorderRadius.circular(20.r),
              ),
              child: Icon(
                activity['icon'] as IconData,
                color: activity['color'] as Color,
                size: 20.w,
              ),
            ),
            title: Text(
              activity['title'] as String,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
            ),
            subtitle: Text(
              activity['subtitle'] as String,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
            ),
            trailing: Text(
              activity['time'] as String,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
                  ),
            ),
          );
        },
      ),
    );
  }
}