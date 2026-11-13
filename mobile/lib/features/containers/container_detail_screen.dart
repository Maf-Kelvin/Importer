import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/confirm.dart';
import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/money.dart';
import '../../core/providers.dart';
import '../expenses/add_expense_sheet.dart';
import '../items/item_actions.dart';
import 'containers_screen.dart';
import 'models.dart';

final containerDetailProvider = FutureProvider.autoDispose.family<ContainerDetail, int>((ref, id) async {
  final r = await ref.read(apiClientProvider).dio.get<Map<String, dynamic>>('/containers/$id');
  return ContainerDetail.fromJson(r.data!);
});

class ContainerDetailScreen extends ConsumerWidget {
  const ContainerDetailScreen({super.key, required this.containerId});
  final int containerId;

  Future<void> _allocate(BuildContext context, WidgetRef ref) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(apiClientProvider).dio.post<dynamic>('/containers/$containerId/allocate-costs');
      ref.invalidate(containerDetailProvider(containerId));
      messenger.showSnackBar(const SnackBar(content: Text('Costs allocated to items')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(containerDetailProvider(containerId));
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(detail.valueOrNull?.name ?? 'Container', overflow: TextOverflow.ellipsis),
          actions: [
            PopupMenuButton<String>(
              onSelected: (v) {
                if (v == 'allocate') _allocate(context, ref);
              },
              itemBuilder: (_) => const [PopupMenuItem(value: 'allocate', child: Text('Allocate costs to items'))],
            ),
          ],
          bottom: const TabBar(tabs: [Tab(text: 'Items'), Tab(text: 'Expenses')]),
        ),
        body: detail.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            padding: const EdgeInsets.all(32),
            children: [
              const SizedBox(height: 60),
              Text(friendlyError(e), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              Center(child: OutlinedButton(onPressed: () => ref.invalidate(containerDetailProvider(containerId)), child: const Text('Try again'))),
            ],
          ),
          data: (c) => Column(
            children: [
              _Summary(c),
              Expanded(
                child: TabBarView(
                  children: [
                    _ItemsTab(c, onChanged: () => ref.invalidate(containerDetailProvider(containerId))),
                    _ExpensesTab(c, onChanged: () {
                      ref.invalidate(containerDetailProvider(containerId));
                      ref.invalidate(containersProvider);
                    }),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary(this.c);
  final ContainerDetail c;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    Widget cell(String label, String value) => Expanded(
          child: Column(
            children: [
              FittedBox(fit: BoxFit.scaleDown, child: Text(value, style: t.titleMedium?.copyWith(fontWeight: FontWeight.w700))),
              Text(label, style: t.bodySmall),
            ],
          ),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          cell('Status', c.status),
          cell('Items', '${c.items.length}'),
          cell('Sold', '${c.itemsSold}'),
          cell('Expenses', money(c.totalExpenses ?? 0)),
        ],
      ),
    );
  }
}

class _ItemsTab extends ConsumerWidget {
  const _ItemsTab(this.c, {required this.onChanged});
  final ContainerDetail c;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton.icon(
            onPressed: () async {
              await context.push('/containers/${c.id}/items/new');
              onChanged();
            },
            icon: const Icon(Icons.add),
            label: const Text('Add item'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          ),
        ),
        if (c.items.isEmpty)
          const Padding(padding: EdgeInsets.all(32), child: Text('No items in this container yet.', textAlign: TextAlign.center))
        else
          for (final i in c.items)
            ListTile(
              minVerticalPadding: 12,
              onTap: i.sold ? () => context.push('/item-media', extra: i) : () => showItemActions(context, ref, i, onChanged: onChanged),
              title: Text(i.name, maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Text(
                '${labelOf(i.category)} · ${labelOf(i.condition)} · '
                '${i.weight == null ? 'no weight' : '${i.weight} kg'}',
              ),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text('${i.purchasePrice.toStringAsFixed(2)} ${i.currency}'),
                  if (i.sold)
                    const Text('Sold', style: TextStyle(fontWeight: FontWeight.w600))
                  else
                    Text('Tap for options', style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
      ],
    );
  }
}

class _ExpensesTab extends ConsumerWidget {
  const _ExpensesTab(this.c, {required this.onChanged});
  final ContainerDetail c;
  final VoidCallback onChanged;

  Future<void> _delete(BuildContext context, WidgetRef ref, ExpenseModel e) async {
    final ok = await confirmDialog(
      context,
      title: 'Delete expense?',
      message: '${labelOf(e.type)} (${e.amount.toStringAsFixed(2)} ${e.currency}) will be removed. Allocate costs again afterwards.',
    );
    if (!ok || !context.mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(apiClientProvider).dio.delete<dynamic>('/expenses/${e.id}');
      onChanged();
    } catch (err) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(err))));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton.icon(
            onPressed: () async {
              final added = await showAddExpenseSheet(context, c.id);
              if (added == true) onChanged();
            },
            icon: const Icon(Icons.add),
            label: const Text('Add expense'),
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
          ),
        ),
        if (c.expenses.isEmpty)
          const Padding(padding: EdgeInsets.all(32), child: Text('No expenses yet.', textAlign: TextAlign.center))
        else
          for (final e in c.expenses)
            ListTile(
              minVerticalPadding: 12,
              onTap: () async {
                final saved = await showAddExpenseSheet(context, c.id, existing: e);
                if (saved == true) onChanged();
              },
              title: Text(labelOf(e.type)),
              subtitle: e.description == null || e.description!.isEmpty ? null : Text(e.description!),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('${e.amount.toStringAsFixed(2)} ${e.currency}'),
                      if (e.currency != 'USD') Text(money(e.amountUsd), style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                  IconButton(
                    tooltip: 'Delete expense',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _delete(context, ref, e),
                  ),
                ],
              ),
            ),
      ],
    );
  }
}
