
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:importer_mobile/main.dart';
import 'package:importer_mobile/features/auth/auth_controller.dart';
import 'package:importer_mobile/features/auth/user.dart';

class FakeAuthController extends AuthController {
  @override
  Future<AppUser?> build() async {
    return null;
  }
}

void main() {
  testWidgets('shows login screen when user is signed out', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authProvider.overrideWith(FakeAuthController.new),
        ],
        child: const ImporterApp(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Importer'), findsOneWidget);
    expect(find.text('Sign in to your organisation'), findsOneWidget);
    expect(find.text('Username'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });
}
