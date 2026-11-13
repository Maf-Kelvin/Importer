import 'package:material_ui/material_ui.dart';
import 'package:flutter_native_contact_picker/flutter_native_contact_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/errors.dart';
import '../../core/idempotency.dart';
import '../../core/providers.dart';

final RegExp _emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

class AddCustomerScreen extends ConsumerStatefulWidget {
  const AddCustomerScreen({super.key});

  @override
  ConsumerState<AddCustomerScreen> createState() => _AddCustomerScreenState();
}

class _AddCustomerScreenState extends ConsumerState<AddCustomerScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _address = TextEditingController();
  bool _busy = false;
  String? _error;
  final String _idempotencyKey = newIdempotencyKey();

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _email.dispose();
    _address.dispose();
    super.dispose();
  }

  /// Opens the phone's own contact picker. The app never reads the address book: it only
  /// receives the one contact the person chooses, and no contacts permission is requested.
  Future<void> _pickFromContacts() async {
    try {
      final contact = await FlutterNativeContactPicker().selectContact();
      if (contact == null) return; // cancelled
      setState(() {
        final name = contact.fullName?.trim();
        if (name != null && name.isNotEmpty) _name.text = name;
        final numbers = contact.phoneNumbers;
        if (numbers != null && numbers.isNotEmpty) _phone.text = numbers.first;
      });
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Could not open your contacts.')));
      }
    }
  }

  Future<void> _save() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    String? opt(TextEditingController c) => c.text.trim().isEmpty ? null : c.text.trim();
    try {
      await ref.read(apiClientProvider).dio.post<dynamic>(
        '/customers/',
        data: {
          'name': _name.text.trim(),
          'phone': opt(_phone),
          'email': opt(_email),
          'address': opt(_address),
        },
        options: idempotencyOptions(_idempotencyKey),
      );
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
      appBar: AppBar(title: const Text('Add customer')),
      body: SafeArea(
        child: Form(
          key: _form,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              OutlinedButton.icon(
                onPressed: _busy ? null : _pickFromContacts,
                icon: const Icon(Icons.contacts_outlined),
                label: const Text('Choose from phone contacts'),
                style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _name,
                textInputAction: TextInputAction.next,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder()),
                validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter a name' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(labelText: 'Phone, optional', border: OutlineInputBorder()),
                validator: (v) => (v != null && v.trim().length > 50) ? 'At most 50 characters' : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autocorrect: false,
                decoration: const InputDecoration(labelText: 'Email, optional', border: OutlineInputBorder()),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  return _emailPattern.hasMatch(v.trim()) ? null : 'Enter a valid email address';
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _address,
                minLines: 2,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Address, optional', border: OutlineInputBorder()),
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
                    : const Text('Save customer'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
