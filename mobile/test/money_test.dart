import 'package:flutter_test/flutter_test.dart';
import 'package:importer_mobile/core/money.dart';

void main() {
  test('formats dollars with separators', () {
    expect(money(0), '\$0.00');
    expect(money(12345.5), '\$12,345.50');
    expect(money(1234567.891), '\$1,234,567.89');
    expect(money(-42), '-\$42.00');
    expect(money(null), '-');
  });
}
