import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/confirm.dart';
import '../../core/errors.dart';
import '../../core/providers.dart';
import '../containers/models.dart';
import '../pricing/price_suggestion_sheet.dart';
import 'mark_sold_sheet.dart';

/// The options for an unsold item. Used from the container screen and the all-items tab.
/// [onChanged] runs after anything that changed the data, so the caller can reload.
Future<void> showItemActions(BuildContext context, WidgetRef ref, ItemModel i, {required VoidCallback onChanged}) async {
  final choice = await showModalBottomSheet<String>(
    context: context,
    showDragHandle: true,
    builder: (ctx) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(title: Text(i.name, style: Theme.of(ctx).textTheme.titleMedium)),
          ListTile(leading: const Icon(Icons.sell_outlined), title: const Text('Mark as sold'), onTap: () => Navigator.of(ctx).pop('sell')),
          ListTile(leading: const Icon(Icons.price_change_outlined), title: const Text('Suggest a selling price'), onTap: () => Navigator.of(ctx).pop('price')),
          ListTile(leading: const Icon(Icons.photo_camera_outlined), title: const Text('Photos & video'), onTap: () => Navigator.of(ctx).pop('media')),
          ListTile(leading: const Icon(Icons.edit_outlined), title: const Text('Edit'), onTap: () => Navigator.of(ctx).pop('edit')),
          ListTile(leading: const Icon(Icons.delete_outline), title: const Text('Delete'), onTap: () => Navigator.of(ctx).pop('delete')),
        ],
      ),
    ),
  );
  if (choice == null || !context.mounted) return;
  switch (choice) {
    case 'sell':
      if (await showMarkSoldSheet(context, i) == true) onChanged();
    case 'price':
      await showPriceSuggestionSheet(context, i);
      onChanged(); // generating a suggestion saves it on the item
    case 'media':
      await context.push('/item-media', extra: i);
    case 'edit':
      await context.push('/item-edit', extra: i);
      onChanged();
    case 'delete':
      final ok = await confirmDialog(context, title: 'Delete item?', message: '"${i.name}" will be removed.');
      if (!ok || !context.mounted) return;
      final messenger = ScaffoldMessenger.of(context);
      try {
        await ref.read(apiClientProvider).dio.delete<dynamic>('/items/${i.id}');
        onChanged();
      } catch (e) {
        messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
      }
  }
}
