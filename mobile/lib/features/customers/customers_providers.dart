import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/paged.dart';
import '../../core/providers.dart';
import 'customer_model.dart';

/// The search text typed on the customers screen ('' = no filter).
final customerSearchProvider = StateProvider.autoDispose<String>((ref) => '');

final customersProvider = FutureProvider.autoDispose<List<Customer>>((ref) async {
  final search = ref.watch(customerSearchProvider).trim();
  final r = await ref.read(apiClientProvider).dio.get<Map<String, dynamic>>(
    '/customers/',
    queryParameters: {'page': 1, 'limit': 100, if (search.isNotEmpty) 'search': search},
  );
  final items = (r.data?['items'] as List?) ?? const [];
  return items.map((e) => Customer.fromJson(e as Map<String, dynamic>)).toList();
});

/// The customers list screen: 30 at a time, restarting from page 1 whenever the search changes.
class CustomersController extends PagedController<Customer> {
  static const _pageSize = 30;

  @override
  Future<PagedState<Customer>> build() {
    ref.watch(customerSearchProvider);
    return fetch(1, const []);
  }

  @override
  Future<PagedState<Customer>> fetch(int page, List<Customer> existing) {
    final search = ref.read(customerSearchProvider).trim();
    return fetchPage(
      ref.read(apiClientProvider).dio,
      '/customers/',
      page: page,
      limit: _pageSize,
      query: {if (search.isNotEmpty) 'search': search},
      parse: Customer.fromJson,
      existing: existing,
    );
  }
}

final customersPageProvider = AutoDisposeAsyncNotifierProvider<CustomersController, PagedState<Customer>>(CustomersController.new);
