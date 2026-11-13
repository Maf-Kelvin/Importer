/// "food_items" -> "Food items"
String labelOf(String slug) {
  if (slug.isEmpty) return slug;
  final spaced = slug.replaceAll('_', ' ');
  return spaced[0].toUpperCase() + spaced.substring(1);
}

/// JSON numbers normally arrive as numbers; accept numeric strings too.
num? asNum(Object? v) {
  if (v == null) return null;
  if (v is num) return v;
  if (v is String) return num.tryParse(v);
  return null;
}

final RegExp _moneyPattern = RegExp(r'^\d+(\.\d{1,4})?$');
final RegExp _weightPattern = RegExp(r'^\d+(\.\d{1,3})?$');

/// Returns the cleaned decimal text, or null when it is not a positive number with allowed places.
String? parsePositiveMoney(String input) {
  final t = input.trim().replaceAll(',', '.');
  if (!_moneyPattern.hasMatch(t)) return null;
  return (num.tryParse(t) ?? 0) > 0 ? t : null;
}

String? parsePositiveWeight(String input) {
  final t = input.trim().replaceAll(',', '.');
  if (!_weightPattern.hasMatch(t)) return null;
  return (num.tryParse(t) ?? 0) > 0 ? t : null;
}

/// 0.256 -> "25.6%". The API sends margins and confidence as ratios, not percentages.
String percent(num? ratio, {int decimals = 1}) {
  if (ratio == null || ratio.isNaN || ratio.isInfinite) return '-';
  return '${(ratio * 100).toStringAsFixed(decimals)}%';
}

/// "25" or "25,5" typed as a percentage -> ratio 0.25, or null when not a number from 5 to 100.
double? parseMarginPercent(String input) {
  final v = double.tryParse(input.trim().replaceAll(',', '.'));
  if (v == null || v < 5 || v > 100) return null;
  return v / 100;
}
