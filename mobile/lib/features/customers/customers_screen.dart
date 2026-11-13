import 'dart:async';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/paged.dart';
import 'customers_providers.dart';

class CustomersScreen extends ConsumerStatefulWidget {
  const CustomersScreen({super.key});

  @override
  ConsumerState<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends ConsumerState<CustomersScreen> {
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
      if (mounted) ref.read(customerSearchProvider.notifier).state = value;
    });
  }

  Future<void> _more() async {
    setState(() => _loadingMore = true);
    final error = await ref.read(customersPageProvider.notifier).loadMore();
    if (!mounted) return;
    setState(() => _loadingMore = false);
    if (error != null) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error)));
  }

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(customersPageProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Customers')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await context.push('/customers/new');
          ref.invalidate(customersPageProvider);
          ref.invalidate(customersProvider);
        },
        icon: const Icon(Icons.person_add_alt_1),
        label: const Text('Add customer'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: TextField(
              onChanged: _onSearch,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                hintText: 'Search by name or email',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(),
                isDense: true,
              ),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.refresh(customersPageProvider.future),
              child: data.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(32),
                  children: [
                    const SizedBox(height: 60),
                    Text(friendlyError(e), textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    Center(child: OutlinedButton(onPressed: () => ref.invalidate(customersPageProvider), child: const Text('Try again'))),
                  ],
                ),
                data: (page) {
                  if (page.items.isEmpty) {
                    return ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(32),
                      children: const [SizedBox(height: 60), Text('No customers found.', textAlign: TextAlign.center)],
                    );
                  }
                  return ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.only(bottom: 88), // room for the button
                    itemCount: page.items.length + 1,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      if (i == page.items.length) {
                        return LoadMoreFooter(
                          shown: page.items.length, total: page.total, hasNext: page.hasNext,
                          loading: _loadingMore, onPressed: _more, noun: 'customer',
                        );
                      }
                      final c = page.items[i];
                      final detail = [c.phone, c.email].whereType<String>().where((s) => s.isNotEmpty).join(' · ');
                      return ListTile(
                        minVerticalPadding: 12,
                        leading: CircleAvatar(child: Text(c.name.isEmpty ? '?' : c.name[0].toUpperCase())),
                        title: Text(c.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                        subtitle: detail.isEmpty ? null : Text(detail, maxLines: 1, overflow: TextOverflow.ellipsis),
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
