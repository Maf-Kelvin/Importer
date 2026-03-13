// lib/presentation/screens/containers/widgets/container_card.dart
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import '../../../../core/utils/helpers.dart';

class ContainerCard extends StatelessWidget {
  final Map<String, dynamic> container;
  final VoidCallback onTap;

  const ContainerCard({
    super.key,
    required this.container,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final itemCount = container['itemCount'] as int;
    final soldCount = container['soldCount'] as int;
    final progress = itemCount > 0 ? soldCount / itemCount : 0.0;
    final status = container['status'] as String;
    final statusColor = Helpers.getStatusColor(status);

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12.r),
        child: Padding(
          padding: EdgeInsets.all(16.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          container['name'],
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                        ),
                        SizedBox(height: 4.h),
                        Text(
                          '${container['type']} Container',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12.r),
                    ),
                    child: Text(
                      status,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 12.sp,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
              
              SizedBox(height: 16.h),

              // Progress section
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Items Progress',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                              ),
                        ),
                        SizedBox(height: 4.h),
                        LinearProgressIndicator(
                          value: progress,
                          backgroundColor: Theme.of(context).colorScheme.surfaceVariant,
                          valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                        ),
                        SizedBox(height: 4.h),
                        Text(
                          '$soldCount of $itemCount sold',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  SizedBox(width: 16.w),
                  Text(
                    '${(progress * 100).toInt()}%',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: statusColor,
                        ),
                  ),
                ],
              ),

              SizedBox(height: 16.h),

              // Metrics row
              Row(
                children: [
                  Expanded(
                    child: _MetricItem(
                      label: 'Total Value',
                      value: Helpers.formatCurrency(container['totalValue'], 'USD'),
                    ),
                  ),
                  Expanded(
                    child: _MetricItem(
                      label: 'Profit',
                      value: Helpers.formatCurrency(container['profit'], 'USD'),
                    ),
                  ),
                  Expanded(
                    child: _MetricItem(
                      label: 'Created',
                      value: Helpers.formatDate(container['createdAt']),
                    ),
                  ),
                ],
              ),

              // MSC tracking number if available
              if (container['mscNumber'] != null) ...[
                SizedBox(height: 12.h),
                Row(
                  children: [
                    Icon(
                      Icons.local_shipping_outlined,
                      size: 16.w,
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    ),
                    SizedBox(width: 8.w),
                    Text(
                      'MSC: ${container['mscNumber']}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                          ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricItem extends StatelessWidget {
  final String label;
  final String value;

  const _MetricItem({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
              ),
        ),
        SizedBox(height: 2.h),
        Text(
          value,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
        ),
      ],
    );
  }
}