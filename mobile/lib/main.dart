import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'router.dart';

void main() {
  runApp(const ProviderScope(child: ImporterApp()));
}

class ImporterApp extends ConsumerWidget {
  const ImporterApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    const seed = Color(0xFF2563EB);
    return MaterialApp.router(
      title: 'Importer',
      debugShowCheckedModeBanner: false,
      routerConfig: ref.watch(routerProvider),
      theme: ThemeData(useMaterial3: true, colorScheme: ColorScheme.fromSeed(seedColor: seed)),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: seed, brightness: Brightness.dark),
      ),
      themeMode: ThemeMode.system,
      // Lets widgets from packages that still use Flutter's old material library (go_router's error page, for
      // one) read this app's theme. Remove once those packages have moved to material_ui.
      builder: (context, child) => MaterialUiCompatibilityBridge(child: child ?? const SizedBox.shrink()),
    );
  }
}
