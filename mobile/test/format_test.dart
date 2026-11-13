import 'package:flutter_test/flutter_test.dart';
import 'package:importer_mobile/core/format.dart';

void main() {
  test('labelOf makes readable labels', () {
    expect(labelOf('food_items'), 'Food items');
    expect(labelOf('new'), 'New');
  });

  test('money input: positive, at most 4 decimals, comma accepted', () {
    expect(parsePositiveMoney('12.50'), '12.50');
    expect(parsePositiveMoney('12,5'), '12.5');
    expect(parsePositiveMoney('0'), isNull);
    expect(parsePositiveMoney('-3'), isNull);
    expect(parsePositiveMoney('1.23456'), isNull);
    expect(parsePositiveMoney('abc'), isNull);
    expect(parsePositiveMoney(''), isNull);
  });

  test('weight input: positive, at most 3 decimals', () {
    expect(parsePositiveWeight('2.5'), '2.5');
    expect(parsePositiveWeight('2.5555'), isNull);
    expect(parsePositiveWeight('0'), isNull);
  });

  test('asNum accepts numbers and numeric strings', () {
    expect(asNum(3), 3);
    expect(asNum('3.5'), 3.5);
    expect(asNum(null), isNull);
    expect(asNum('x'), isNull);
  });

  test('percent: the API sends ratios', () {
    expect(percent(0.256), '25.6%');
    expect(percent(0.25, decimals: 0), '25%');
    expect(percent(0), '0.0%');
    expect(percent(null), '-');
  });

  test('margin input is a percentage between 5 and 100', () {
    expect(parseMarginPercent('25'), 0.25);
    expect(parseMarginPercent('12,5'), 0.125);
    expect(parseMarginPercent('4'), isNull);
    expect(parseMarginPercent('101'), isNull);
    expect(parseMarginPercent('abc'), isNull);
  });
}
