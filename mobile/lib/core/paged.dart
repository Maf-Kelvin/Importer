import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'errors.dart';

/// Items loaded so far from a paged API list (`items,total,page,has_next`).
class PagedState<T> {
  const PagedState({required this.items, required this.total, required this.page, required this.hasNext});
  final List<T> items;
  final int total;
  final int page;
  final bool hasNext;
}

/// Fetches one page and appends it to [existing].
Future<PagedState<T>> fetchPage<T>(
  Dio dio,
  String path, {
  required int page,
  required int limit,
  required T Function(Map<String, dynamic>) parse,
  Map<String, dynamic>? query,
  List<T> existing = const [],
}) async {
  final r = await dio.get<Map<String, dynamic>>(path, queryParameters: {...?query, 'page': page, 'limit': limit});
  final data = r.data ?? const <String, dynamic>{};
  final fresh = ((data['items'] as List?) ?? const []).map((e) => parse(e as Map<String, dynamic>)).toList();
  return PagedState<T>(
    items: [...existing, ...fresh],
    total: (data['total'] as num?)?.toInt() ?? existing.length + fresh.length,
    page: page,
    hasNext: (data['has_next'] as bool?) ?? false,
  );
}

/// Base for a list that loads page by page. Subclasses say how to fetch a page; `build()` should
/// return `fetch(1, const [])` (and `ref.watch` whatever filters it depends on).
abstract class PagedController<T> extends AutoDisposeAsyncNotifier<PagedState<T>> {
  Future<PagedState<T>> fetch(int page, List<T> existing);

  /// Returns an error message, or null on success. A failure keeps the list already on screen.
  Future<String?> loadMore() async {
    final current = state.valueOrNull;
    if (current == null || !current.hasNext) return null;
    try {
      state = AsyncData(await fetch(current.page + 1, current.items));
      return null;
    } catch (e) {
      return friendlyError(e);
    }
  }
}

/// The "Load more (30 of 120)" button at the end of a list.
class LoadMoreFooter extends StatelessWidget {
  const LoadMoreFooter({super.key, required this.shown, required this.total, required this.hasNext, required this.loading, required this.onPressed, required this.noun});
  final int shown;
  final int total;
  final bool hasNext;
  final bool loading;
  final VoidCallback onPressed;
  final String noun; // singular, e.g. "container"

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: hasNext
          ? OutlinedButton(
              onPressed: loading ? null : onPressed,
              child: loading
                  ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text('Load more ($shown of $total)'),
            )
          : Center(child: Text('$total $noun${total == 1 ? '' : 's'}')),
    );
  }
}
