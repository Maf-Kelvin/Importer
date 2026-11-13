import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/idempotency.dart';
import '../../core/providers.dart';
import '../containers/models.dart';

const _types = ['loading_fee', 'shipping_fee', 'clearing_fee', 'offloading_fee', 'warehouse_fee', 'security_fee', 'extra_fee'];
const _currencies = ['USD', 'EUR', 'CZK', 'NGN'];

/// Returns true when an expense was added.
Future<bool?> showAddExpenseSheet(BuildContext context, int containerId, {ExpenseModel? existing}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _AddExpenseSheet(containerId: containerId, existing: existing),
  );
}

class _AddExpenseSheet extends ConsumerStatefulWidget {
  const _AddExpenseSheet({required this.containerId, this.existing});
  final int containerId;
  final ExpenseModel? existing;

  @override
  ConsumerState<_AddExpenseSheet> createState() => _AddExpenseSheetState();
}

class _AddExpenseSheetState extends ConsumerState<_AddExpenseSheet> {
  final _form = GlobalKey<FormState>();
  final _amount = TextEditingController();
  final _description = TextEditingController();
  String _type = 'shipping_fee';
  String _currency = 'USD';
  bool _busy = false;
  String? _error;
  final String _idempotencyKey = newIdempotencyKey();

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    if (e != null) {
      _amount.text = e.amount.toString();
      _description.text = e.description ?? '';
      if (_types.contains(e.type)) _type = e.type;
      if (_currencies.contains(e.currency)) _currency = e.currency;
    }
  }

  @override
  void dispose() {
    _amount.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final edit = widget.existing;
      final dio = ref.read(apiClientProvider).dio;
      final body = <String, dynamic>{
        if (edit == null) 'container_id': widget.containerId,
        'expense_type': _type,
        'amount': parsePositiveMoney(_amount.text),
        'currency': _currency,
        if (_description.text.trim().isNotEmpty) 'description': _description.text.trim() else if (edit != null) 'description': null,
      };
      if (edit == null) {
        await dio.post<dynamic>('/expenses/', data: body, options: idempotencyOptions(_idempotencyKey));
      } else {
        await dio.put<dynamic>('/expenses/${edit.id}', data: body);
      }
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(widget.existing == null ? 'Add expense' : 'Edit expense', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _type,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Type', border: OutlineInputBorder()),
                items: [for (final t in _types) DropdownMenuItem(value: t, child: Text(labelOf(t)))],
                onChanged: (v) => setState(() => _type = v ?? _type),
              ),
              const SizedBox(height: 16),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 3,
                    child: TextFormField(
                      controller: _amount,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Amount', border: OutlineInputBorder()),
                      validator: (v) => parsePositiveMoney(v ?? '') == null ? 'Enter an amount above 0' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: DropdownButtonFormField<String>(
                      initialValue: _currency,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Currency', border: OutlineInputBorder()),
                      items: [for (final c in _currencies) DropdownMenuItem(value: c, child: Text(c))],
                      onChanged: (v) => setState(() => _currency = v ?? _currency),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _description,
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
                    : Text(widget.existing == null ? 'Save expense' : 'Save changes'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
