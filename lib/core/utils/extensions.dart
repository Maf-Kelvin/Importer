// lib/core/utils/extensions.dart
extension StringExtensions on String {
  String get capitalize => Helpers.capitalize(this);
  String get capitalizeWords => Helpers.capitalizeWords(this);
  String get formatCategory => Helpers.formatCategoryName(this);
  
  bool get isValidEmail => Helpers.isValidEmail(this);
  bool get isValidPhoneNumber => Helpers.isValidPhoneNumber(this);
}

extension DoubleExtensions on double {
  String formatCurrency(String currency) => Helpers.formatCurrency(this, currency);
  String get formatNumber => Helpers.formatNumber(this);
  String get formatWeight => Helpers.formatWeight(this);
  String get formatVolume => Helpers.formatVolume(this);
  String get formatPercentage => Helpers.formatPercentage(this);
}

extension DateTimeExtensions on DateTime {
  String get formatDate => Helpers.formatDate(this);
  String get formatDateTime => Helpers.formatDateTime(this);
  String get formatTime => Helpers.formatTime(this);
  
  bool get isToday {
    final now = DateTime.now();
    return year == now.year && month == now.month && day == now.day;
  }
  
  bool get isYesterday {
    final yesterday = DateTime.now().subtract(const Duration(days: 1));
    return year == yesterday.year && 
           month == yesterday.month && 
           day == yesterday.day;
  }
}

extension ListExtensions on List {
  bool get isNotNullOrEmpty => isNotEmpty;
  bool get isNullOrEmpty => isEmpty;
}