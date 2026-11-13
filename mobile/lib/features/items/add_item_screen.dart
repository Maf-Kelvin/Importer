import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/format.dart';
import '../../core/idempotency.dart';
import '../../core/providers.dart';
import '../containers/container_detail_screen.dart';
import '../containers/models.dart';

const _categories = ['electronics', 'vehicles', 'engines', 'appliances', 'food_items', 'laptops', 'other'];
const _conditions = ['new', 'tokunbo', 'used'];
const _currencies = ['USD', 'EUR', 'CZK', 'NGN'];

class AddItemScreen extends ConsumerStatefulWidget {
  const AddItemScreen({super.key, required this.containerId, this.existing});
  final int containerId;

  /// When set, the form edits this item instead of adding a new one.
  final ItemModel? existing;

  @override
  ConsumerState<AddItemScreen> createState() => _AddItemScreenState();
}

class _AddItemScreenState extends ConsumerState<AddItemScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _price = TextEditingController();
  final _weight = TextEditingController();
  final _description = TextEditingController();
  String _category = 'other';
  String _condition = 'new';
  String _currency = 'USD';
  bool _busy = false;
  String? _error;
  // One key for this form: a retry after a lost response must not create the item twice.
  final String _idempotencyKey = newIdempotencyKey();
  bool _suggesting = false;
  String? _suggestionNote;

  bool get _editing => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    if (e != null) {
      _name.text = e.name;
      _price.text = e.purchasePrice.toString();
      _weight.text = e.weight?.toString() ?? '';
      _description.text = e.description ?? '';
      if (_categories.contains(e.category)) _category = e.category;
      if (_conditions.contains(e.condition)) _condition = e.condition;
      if (_currencies.contains(e.currency)) _currency = e.currency;
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _price.dispose();
    _weight.dispose();
    _description.dispose();
    super.dispose();
  }

  /// Asks the server for an ESTIMATED weight from the name. The person must check it: nothing is saved here.
  Future<void> _suggestWeight() async {
    if (_name.text.trim().isEmpty) {
      setState(() => _suggestionNote = 'Type the item name first.');
      return;
    }
    setState(() {
      _suggesting = true;
      _suggestionNote = null;
    });
    try {
      final r = await ref.read(apiClientProvider).dio.post<Map<String, dynamic>>('/items/suggest-weight', data: {
        'name': _name.text.trim(),
        'category': _category,
        'condition': _condition,
        if (_description.text.trim().isNotEmpty) 'description': _description.text.trim(),
      });
      final kg = asNum(r.data?['weight_kg']);
      final confidence = (r.data?['confidence'] as String?) ?? 'low';
      if (kg != null && mounted) {
        setState(() {
          _weight.text = kg.toString();
          _suggestionNote = 'Estimate ($confidence confidence). Please check it before saving.';
        });
      }
    } catch (e) {
      if (mounted) setState(() => _suggestionNote = friendlyError(e));
    } finally {
      if (mounted) setState(() => _suggesting = false);
    }
  }

  Future<void> _save() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final weight = _weight.text.trim().isEmpty ? null : parsePositiveWeight(_weight.text);
    final edit = widget.existing;
    final body = <String, dynamic>{
      if (edit == null) 'container_id': widget.containerId,
      'name': _name.text.trim(),
      'category': _category,
      'condition': _condition,
      'purchase_price': parsePositiveMoney(_price.text),
      'purchase_currency': _currency,
      // adding: leave weight out when unknown. editing: send null to clear it.
      if (weight != null) 'weight': weight else if (edit != null) 'weight': null,
      if (_description.text.trim().isNotEmpty) 'description': _description.text.trim(),
    };
    try {
      final dio = ref.read(apiClientProvider).dio;
      if (edit == null) {
        await dio.post<dynamic>('/items/', data: body, options: idempotencyOptions(_idempotencyKey));
      } else {
        await dio.put<dynamic>('/items/${edit.id}', data: body);
      }
      ref.invalidate(containerDetailProvider(widget.containerId));
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_editing ? 'Edit item' : 'Add item')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              TextFormField(
                controller: _name,
                textInputAction: TextInputAction.next,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder()),
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter a name' : null,
              ),
              const SizedBox(height: 16),
              _Dropdown(label: 'Category', value: _category, options: _categories, onChanged: (v) => setState(() => _category = v)),
              const SizedBox(height: 16),
              _Dropdown(label: 'Condition', value: _condition, options: _conditions, onChanged: (v) => setState(() => _condition = v)),
              const SizedBox(height: 16),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    flex: 3,
                    child: TextFormField(
                      controller: _price,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(labelText: 'Purchase price', border: OutlineInputBorder()),
                      validator: (v) => parsePositiveMoney(v ?? '') == null ? 'Enter an amount above 0' : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    flex: 2,
                    child: _Dropdown(label: 'Currency', value: _currency, options: _currencies, raw: true, onChanged: (v) => setState(() => _currency = v)),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _weight,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Weight (kg), optional',
                  helperText: 'Only needed to split costs by weight',
                  border: OutlineInputBorder(),
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null; // optional
                  return parsePositiveWeight(v) == null ? 'Enter a weight above 0 (up to 3 decimals)' : null;
                },
              ),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: _suggesting ? null : _suggestWeight,
                  icon: _suggesting
                      ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_outlined),
                  label: const Text('Suggest weight from name'),
                ),
              ),
              if (_suggestionNote != null) Text(_suggestionNote!, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 16),
              TextFormField(
                controller: _description,
                minLines: 2,
                maxLines: 4,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(labelText: 'Description, optional', border: OutlineInputBorder()),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _busy ? null : _save,
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                child: _busy
                    ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2.5))
                    : Text(_editing ? 'Save changes' : 'Save item'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dropdown extends StatelessWidget {
  const _Dropdown({required this.label, required this.value, required this.options, required this.onChanged, this.raw = false});
  final String label;
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;
  final bool raw; // show the value as is (currency codes) instead of a readable label

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
      items: [for (final o in options) DropdownMenuItem(value: o, child: Text(raw ? o : labelOf(o)))],
      onChanged: (v) {
        if (v != null) onChanged(v);
      },
    );
  }
}
