import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/money.dart';
import '../../core/providers.dart';
import '../containers/models.dart';

Future<void> showPriceSuggestionSheet(BuildContext context, ItemModel item) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _PriceSheet(item: item),
  );
}

class _PriceSheet extends ConsumerStatefulWidget {
  const _PriceSheet({required this.item});
  final ItemModel item;

  @override
  ConsumerState<_PriceSheet> createState() => _PriceSheetState();
}

class _PriceSheetState extends ConsumerState<_PriceSheet> {
  Map<String, dynamic>? _result;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Cost-based plus the organisation's own past sales. Online market lookup stays off here: it depends on
      // outside websites and is slower; it is available on the web app.
      final r = await ref.read(apiClientProvider).dio.post<Map<String, dynamic>>(
        '/pricing/generate/${widget.item.id}',
        data: {'include_cost_based': true, 'include_market_pricing': false, 'include_last_sold': true},
      );
      if (mounted) setState(() => _result = r.data);
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    Widget body;
    if (_loading) {
      body = const Padding(padding: EdgeInsets.all(32), child: Center(child: CircularProgressIndicator()));
    } else if (_error != null) {
      body = Column(children: [
        Text(_error!, textAlign: TextAlign.center),
        const SizedBox(height: 12),
        OutlinedButton(onPressed: _load, child: const Text('Try again')),
      ]);
    } else {
      final r = _result ?? const {};
      final recommended = asNum(r['recommended_price']);
      final low = asNum(r['price_low']);
      final high = asNum(r['price_high']);
      final warnings = ((r['warnings'] as List?) ?? const []).map((e) => e.toString()).toList();
      final why = ((r['explanation'] as List?) ?? const []).map((e) => e.toString()).toList();
      body = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Text(recommended == null ? 'No suggestion yet' : money(recommended),
                style: t.displaySmall?.copyWith(fontWeight: FontWeight.w700)),
          ),
          if (low != null && high != null) Center(child: Text('Range ${money(low)} to ${money(high)}')),
          const SizedBox(height: 16),
          _row('Landed cost', money(asNum(r['landed_cost']))),
          _row('Expected margin', percent(asNum(r['expected_margin']))),
          _row('Confidence', percent(asNum(r['confidence']), decimals: 0)),
          _row('Comparable prices used', '${asNum(r['comparables_used']) ?? 0}'),
          if (warnings.isNotEmpty) ...[
            const SizedBox(height: 12),
            for (final w in warnings) Text('! $w', style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          if (why.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('How this was worked out', style: t.titleSmall),
            for (final line in why) Padding(padding: const EdgeInsets.only(top: 4), child: Text(line, style: t.bodySmall)),
          ],
          const SizedBox(height: 12),
          Text('The suggested price is saved on the item. You still choose the price you sell at.', style: t.bodySmall),
        ],
      );
    }
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Selling price for', style: t.bodySmall),
            Text(widget.item.name, style: t.titleLarge, maxLines: 1, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 12),
            body,
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(label), Text(value, style: const TextStyle(fontWeight: FontWeight.w600))]),
      );
}
