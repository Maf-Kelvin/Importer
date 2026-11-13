import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/money.dart';
import '../../core/providers.dart';

final containerReportsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final r = await ref.read(apiClientProvider).dio.get<List<dynamic>>('/reports/profit/containers');
  return (r.data ?? const []).cast<Map<String, dynamic>>();
});

final categoryReportsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final r = await ref.read(apiClientProvider).dio.get<List<dynamic>>('/reports/profit/categories');
  return (r.data ?? const []).cast<Map<String, dynamic>>();
});

num _n(Map<String, dynamic> m, String k) => asNum(m[k]) ?? 0;

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Reports'),
          bottom: const TabBar(tabs: [Tab(text: 'By container'), Tab(text: 'By category')]),
        ),
        body: const TabBarView(children: [_ContainersReport(), _CategoriesReport()]),
      ),
    );
  }
}

class _ReportList extends StatelessWidget {
  const _ReportList({required this.rows, required this.emptyText, required this.card, required this.onRefresh});
  final List<Map<String, dynamic>> rows;
  final String emptyText;
  final Widget Function(Map<String, dynamic>) card;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: rows.isEmpty
          ? ListView(physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.all(32), children: [const SizedBox(height: 60), Text(emptyText, textAlign: TextAlign.center)])
          : ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(12),
              itemCount: rows.length,
              itemBuilder: (_, i) => card(rows[i]),
            ),
    );
  }
}

class _Failure extends StatelessWidget {
  const _Failure({required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final forbidden = error is DioException && (error as DioException).response?.statusCode == 403;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(32),
      children: [
        const SizedBox(height: 60),
        Text(forbidden ? 'Only managers and administrators can see this report.' : friendlyError(error), textAlign: TextAlign.center),
        if (!forbidden) ...[
          const SizedBox(height: 16),
          Center(child: OutlinedButton(onPressed: onRetry, child: const Text('Try again'))),
        ],
      ],
    );
  }
}

class _Line extends StatelessWidget {
  const _Line(this.label, this.value, {this.bold = false});
  final String label;
  final String value;
  final bool bold;

  @override
  Widget build(BuildContext context) {
    final style = bold ? const TextStyle(fontWeight: FontWeight.w700) : null;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(children: [Expanded(child: Text(label)), Text(value, style: style)]),
    );
  }
}

class _ContainersReport extends ConsumerWidget {
  const _ContainersReport();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(containerReportsProvider);
    return data.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => _Failure(error: e, onRetry: () => ref.invalidate(containerReportsProvider)),
      data: (rows) => _ReportList(
        rows: rows,
        emptyText: 'No containers yet.',
        onRefresh: () => ref.refresh(containerReportsProvider.future),
        card: (m) => Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text((m['container_name'] as String?) ?? 'Container', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _Line('Items sold', '${_n(m, 'items_sold').toInt()} of ${_n(m, 'total_items').toInt()}'),
                _Line('Revenue', money(_n(m, 'total_revenue'))),
                _Line('Total cost', money(_n(m, 'total_cost'))),
                _Line('Profit', money(_n(m, 'total_profit')), bold: true),
                _Line('Margin', percent(asNum(m['profit_margin']))),
                _Line('Unsold stock', money(_n(m, 'inventory_value'))),
                if (_n(m, 'unallocated_expenses') > 0) _Line('Expenses not yet allocated', money(_n(m, 'unallocated_expenses'))),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CategoriesReport extends ConsumerWidget {
  const _CategoriesReport();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(categoryReportsProvider);
    return data.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => _Failure(error: e, onRetry: () => ref.invalidate(categoryReportsProvider)),
      data: (rows) => _ReportList(
        rows: rows,
        emptyText: 'No sales data yet.',
        onRefresh: () => ref.refresh(categoryReportsProvider.future),
        card: (m) => Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(labelOf((m['category'] as String?) ?? ''), style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                _Line('Items sold', '${_n(m, 'items_sold').toInt()} of ${_n(m, 'total_items').toInt()}'),
                _Line('Revenue', money(_n(m, 'total_revenue'))),
                _Line('Profit', money(_n(m, 'total_profit')), bold: true),
                _Line('Average margin', percent(asNum(m['average_margin']))),
                _Line('Unsold stock', money(_n(m, 'inventory_value'))),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
