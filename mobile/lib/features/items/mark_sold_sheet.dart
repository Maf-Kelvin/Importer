import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/idempotency.dart';
import '../../core/providers.dart';
import '../containers/models.dart';
import '../customers/customers_providers.dart';

/// Returns true when the sale was recorded.
Future<bool?> showMarkSoldSheet(BuildContext context, ItemModel item) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _MarkSoldSheet(item: item),
  );
}

String _isoDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

class _MarkSoldSheet extends ConsumerStatefulWidget {
  const _MarkSoldSheet({required this.item});
  final ItemModel item;

  @override
  ConsumerState<_MarkSoldSheet> createState() => _MarkSoldSheetState();
}

class _MarkSoldSheetState extends ConsumerState<_MarkSoldSheet> {
  final _form = GlobalKey<FormState>();
  final _price = TextEditingController();
  final _notes = TextEditingController();
  DateTime _date = DateTime.now();
  int? _customerId;
  bool _busy = false;
  String? _error;
  final String _idempotencyKey = newIdempotencyKey();

  @override
  void dispose() {
    _price.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2000),
      lastDate: DateTime.now().add(const Duration(days: 1)),
    );
    if (picked != null) setState(() => _date = picked);
  }

  Future<void> _save() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).dio.post<dynamic>(
        '/items/${widget.item.id}/mark-sold',
        data: {
          'selling_price': parsePositiveMoney(_price.text),
          'sold_date': _isoDate(_date),
          if (_customerId != null) 'customer_id': _customerId,
          if (_notes.text.trim().isNotEmpty) 'notes': _notes.text.trim(),
        },
        options: idempotencyOptions(_idempotencyKey),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final customers = ref.watch(customersProvider);
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Mark as sold', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              Text(widget.item.name, maxLines: 1, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 16),
              TextFormField(
                controller: _price,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Selling price (USD)', border: OutlineInputBorder()),
                validator: (v) => parsePositiveMoney(v ?? '') == null ? 'Enter an amount above 0' : null,
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _pickDate,
                icon: const Icon(Icons.calendar_today_outlined),
                label: Text('Sold on ${_isoDate(_date)}'),
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
              ),
              const SizedBox(height: 16),
              customers.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, __) => const Text('Customers could not be loaded; you can still record the sale without one.'),
                data: (list) => DropdownButtonFormField<int?>(
                  initialValue: _customerId,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Customer, optional', border: OutlineInputBorder()),
                  items: [
                    const DropdownMenuItem<int?>(value: null, child: Text('No customer')),
                    for (final c in list) DropdownMenuItem<int?>(value: c.id, child: Text(c.name, overflow: TextOverflow.ellipsis)),
                  ],
                  onChanged: (v) => setState(() => _customerId = v),
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _notes,
                decoration: const InputDecoration(labelText: 'Note, optional', border: OutlineInputBorder()),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _busy ? null : _save,
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                child: _busy
                    ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                    : const Text('Record sale'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
