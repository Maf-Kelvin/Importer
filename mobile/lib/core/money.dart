/// Formats a dollar amount with thousands separators, e.g. 12345.5 -> $12,345.50
String money(num? value) {
  if (value == null) return '-';
  final negative = value < 0;
  final fixed = value.abs().toStringAsFixed(2);
  final parts = fixed.split('.');
  final whole = parts[0];
  final buf = StringBuffer();
  for (var i = 0; i < whole.length; i++) {
    if (i > 0 && (whole.length - i) % 3 == 0) buf.write(',');
    buf.write(whole[i]);
  }
  return '${negative ? '-' : ''}\$$buf.${parts[1]}';
}
