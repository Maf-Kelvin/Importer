import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/paged.dart';
import '../../core/providers.dart';

class ContainerSummary {
  const ContainerSummary({required this.id, required this.name, required this.type, required this.sealed, required this.shipped});
  final int id;
  final String name;
  final String type;
  final bool sealed;
  final bool shipped;

  factory ContainerSummary.fromJson(Map<String, dynamic> j) => ContainerSummary(
        id: j['id'] as int,
        name: j['name'] as String,
        type: (j['container_type'] as String?) ?? '',
        sealed: (j['is_sealed'] as bool?) ?? false,
        shipped: (j['is_shipped'] as bool?) ?? false,
      );

  String get status => shipped ? 'Shipped' : (sealed ? 'Sealed' : 'Open');
}

class ContainersController extends PagedController<ContainerSummary> {
  static const _pageSize = 30;

  @override
  Future<PagedState<ContainerSummary>> build() => fetch(1, const []);

  @override
  Future<PagedState<ContainerSummary>> fetch(int page, List<ContainerSummary> existing) => fetchPage(
        ref.read(apiClientProvider).dio,
        '/containers/',
        page: page,
        limit: _pageSize,
        parse: ContainerSummary.fromJson,
        existing: existing,
      );
}

final containersProvider = AutoDisposeAsyncNotifierProvider<ContainersController, PagedState<ContainerSummary>>(ContainersController.new);

class ContainersScreen extends ConsumerStatefulWidget {
  const ContainersScreen({super.key});

  @override
  ConsumerState<ContainersScreen> createState() => _ContainersScreenState();
}

class _ContainersScreenState extends ConsumerState<ContainersScreen> {
  bool _loadingMore = false;

  Future<void> _more() async {
    setState(() => _loadingMore = true);
    final error = await ref.read(containersProvider.notifier).loadMore();
    if (!mounted) return;
    setState(() => _loadingMore = false);
    if (error != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error)));
  }

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(containersProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Containers')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(containersProvider.future),
        child: data.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(32),
            children: [
              const SizedBox(height: 80),
              Text(friendlyError(e), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              Center(child: OutlinedButton(onPressed: () => ref.invalidate(containersProvider), child: const Text('Try again'))),
            ],
          ),
          data: (page) {
            if (page.items.isEmpty) {
              return ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(32),
                children: const [SizedBox(height: 80), Text('No containers yet.', textAlign: TextAlign.center)],
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: page.items.length + 1,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                if (i == page.items.length) {
                  return LoadMoreFooter(
                    shown: page.items.length, total: page.total, hasNext: page.hasNext,
                    loading: _loadingMore, onPressed: _more, noun: 'container',
                  );
                }
                final c = page.items[i];
                return ListTile(
                  minVerticalPadding: 14,
                  title: Text(c.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text(c.type),
                  trailing: Chip(label: Text(c.status), visualDensity: VisualDensity.compact),
                  onTap: () => context.push('/containers/${c.id}'),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
