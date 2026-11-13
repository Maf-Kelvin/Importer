import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/money.dart';
import '../../core/providers.dart';

final dashboardProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final r = await ref.read(apiClientProvider).dio.get<Map<String, dynamic>>('/reports/dashboard');
  return r.data!;
});

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(dashboardProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(tooltip: 'Reports', icon: const Icon(Icons.bar_chart), onPressed: () => context.push('/reports')),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(dashboardProvider.future),
        child: data.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => _ErrorView(message: friendlyError(e), onRetry: () => ref.invalidate(dashboardProvider)),
          data: (d) {
            num n(String k) => (d[k] as num?) ?? 0;
            final tiles = <(String, String, String?)>[
              ('Revenue', money(n('total_revenue')), 'Sold items'),
              ('Cost of goods sold', money(n('cost_of_goods_sold')), 'Landed cost of sold'),
              ('Profit', money(n('total_profit')), '${percent(n('avg_profit_margin'))} margin'),
              ('Inventory value', money(n('inventory_value')), 'Unsold, at landed cost'),
              ('Containers', '${n('active_containers').toInt()}', null),
              ('Items sold', '${n('items_sold').toInt()} / ${n('total_items').toInt()}', null),
              ('Shipments pending', '${n('pending_shipments').toInt()}', null),
              ('Low-stock alerts', '${n('low_stock_alerts').toInt()}', null),
            ];
            return ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 1.35,
                  children: [for (final t in tiles) _StatCard(label: t.$1, value: t.$2, hint: t.$3)],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, this.hint});
  final String label;
  final String value;
  final String? hint;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: t.labelLarge),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(value, style: t.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
            ),
            Text(hint ?? ' ', style: t.bodySmall, maxLines: 1, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 80),
        Text(message, textAlign: TextAlign.center),
        const SizedBox(height: 16),
        Center(child: OutlinedButton(onPressed: onRetry, child: const Text('Try again'))),
      ],
    );
  }
}
