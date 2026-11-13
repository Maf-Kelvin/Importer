import 'dart:async';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/providers.dart';
import '../containers/models.dart';
import 'item_actions.dart';

enum ItemFilter { all, inStock, sold }

final itemSearchProvider = StateProvider.autoDispose<String>((ref) => '');
final itemFilterProvider = StateProvider.autoDispose<ItemFilter>((ref) => ItemFilter.all);

class ItemsPageState {
  const ItemsPageState({required this.items, required this.total, required this.page, required this.hasNext});
  final List<ItemModel> items;
  final int total;
  final int page;
  final bool hasNext;
}

/// All items of the organisation, 30 at a time. Changing the search or filter starts again from page 1.
class ItemsController extends AutoDisposeAsyncNotifier<ItemsPageState> {
  static const _pageSize = 30;

  @override
  Future<ItemsPageState> build() {
    final search = ref.watch(itemSearchProvider).trim();
    final filter = ref.watch(itemFilterProvider);
    return _fetch(1, search, filter, const []);
  }

  Future<ItemsPageState> _fetch(int page, String search, ItemFilter filter, List<ItemModel> existing) async {
    final r = await ref.read(apiClientProvider).dio.get<Map<String, dynamic>>(
      '/items/',
      queryParameters: {
        'page': page,
        'limit': _pageSize,
        if (search.isNotEmpty) 'search': search,
        if (filter == ItemFilter.inStock) 'sold': false,
        if (filter == ItemFilter.sold) 'sold': true,
      },
    );
    final data = r.data ?? const <String, dynamic>{};
    final fresh = ((data['items'] as List?) ?? const []).map((e) => ItemModel.fromJson(e as Map<String, dynamic>)).toList();
    return ItemsPageState(
      items: [...existing, ...fresh],
      total: (data['total'] as num?)?.toInt() ?? existing.length + fresh.length,
      page: page,
      hasNext: (data['has_next'] as bool?) ?? false,
    );
  }

  /// Returns an error message, or null on success. A failure keeps the list already on screen.
  Future<String?> loadMore() async {
    final current = state.valueOrNull;
    if (current == null || !current.hasNext) return null;
    try {
      final next = await _fetch(current.page + 1, ref.read(itemSearchProvider).trim(), ref.read(itemFilterProvider), current.items);
      state = AsyncData(next);
      return null;
    } catch (e) {
      return friendlyError(e);
    }
  }
}

final itemsControllerProvider = AutoDisposeAsyncNotifierProvider<ItemsController, ItemsPageState>(ItemsController.new);

class ItemsScreen extends ConsumerStatefulWidget {
  const ItemsScreen({super.key});

  @override
  ConsumerState<ItemsScreen> createState() => _ItemsScreenState();
}

class _ItemsScreenState extends ConsumerState<ItemsScreen> {
  Timer? _debounce;
  bool _loadingMore = false;

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    // wait until typing pauses, so each keystroke does not hit the server
    _debounce = Timer(const Duration(milliseconds: 400), () {
      if (mounted) ref.read(itemSearchProvider.notifier).state = value;
    });
  }

  Future<void> _more() async {
    setState(() => _loadingMore = true);
    final error = await ref.read(itemsControllerProvider.notifier).loadMore();
    if (!mounted) return;
    setState(() => _loadingMore = false);
    if (error != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error)));
  }

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(itemsControllerProvider);
    final filter = ref.watch(itemFilterProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Items')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: TextField(
              onChanged: _onSearch,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(hintText: 'Search items by name', prefixIcon: Icon(Icons.search), border: OutlineInputBorder(), isDense: true),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Wrap(
              spacing: 8,
              children: [
                for (final f in ItemFilter.values)
                  ChoiceChip(
                    label: Text(switch (f) { ItemFilter.all => 'All', ItemFilter.inStock => 'In stock', ItemFilter.sold => 'Sold' }),
                    selected: filter == f,
                    onSelected: (_) => ref.read(itemFilterProvider.notifier).state = f,
                  ),
              ],
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.refresh(itemsControllerProvider.future),
              child: data.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(32),
                  children: [
                    const SizedBox(height: 60),
                    Text(friendlyError(e), textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    Center(child: OutlinedButton(onPressed: () => ref.invalidate(itemsControllerProvider), child: const Text('Try again'))),
                  ],
                ),
                data: (page) {
                  if (page.items.isEmpty) {
                    return ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(32),
                      children: const [SizedBox(height: 60), Text('No items found.', textAlign: TextAlign.center)],
                    );
                  }
                  return ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    itemCount: page.items.length + 1,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      if (i == page.items.length) {
                        return Padding(
                          padding: const EdgeInsets.all(16),
                          child: page.hasNext
                              ? OutlinedButton(
                                  onPressed: _loadingMore ? null : _more,
                                  child: _loadingMore
                                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                                      : Text('Load more (${page.items.length} of ${page.total})'),
                                )
                              : Center(child: Text('${page.total} item${page.total == 1 ? '' : 's'}')),
                        );
                      }
                      final item = page.items[i];
                      return ListTile(
                        minVerticalPadding: 12,
                        onTap: item.sold
                            ? () => context.push('/item-media', extra: item)
                            : () => showItemActions(context, ref, item, onChanged: () => ref.invalidate(itemsControllerProvider)),
                        title: Text(item.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: Text('${labelOf(item.category)} · ${labelOf(item.condition)}'),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('${item.purchasePrice.toStringAsFixed(2)} ${item.currency}'),
                            Text(item.sold ? 'Sold · tap for photos' : 'Tap for options', style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
