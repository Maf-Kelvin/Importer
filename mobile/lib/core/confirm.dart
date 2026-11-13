import 'package:material_ui/material_ui.dart';

/// Asks "are you sure?" before something that cannot be undone from the app.
Future<bool> confirmDialog(BuildContext context, {required String title, required String message, String action = 'Delete'}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: Text(action)),
      ],
    ),
  );
  return result ?? false;
}
