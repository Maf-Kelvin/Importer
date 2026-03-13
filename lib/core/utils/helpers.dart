// lib/core/utils/helpers.dart
import 'package:intl/intl.dart';

class Helpers {
  // Currency Formatting
  static String formatCurrency(double amount, String currency) {
    final formatter = NumberFormat.currency(
      symbol: AppConstants.currencySymbols[currency] ?? currency,
      decimalDigits: 2,
    );
    return formatter.format(amount);
  }
  
  // Date Formatting
  static String formatDate(DateTime date) {
    return DateFormat('MMM dd, yyyy').format(date);
  }
  
  static String formatDateTime(DateTime date) {
    return DateFormat('MMM dd, yyyy HH:mm').format(date);
  }
  
  static String formatTime(DateTime date) {
    return DateFormat('HH:mm').format(date);
  }
  
  // Number Formatting
  static String formatNumber(double number, {int decimals = 2}) {
    return NumberFormat('#,##0.${'0' * decimals}').format(number);
  }
  
  static String formatWeight(double weight) {
    return '${formatNumber(weight, decimals: 1)} kg';
  }
  
  static String formatVolume(double volume) {
    return '${formatNumber(volume, decimals: 2)} m³';
  }
  
  // Percentage
  static String formatPercentage(double value) {
    return '${(value * 100).toStringAsFixed(1)}%';
  }
  
  // String Utilities
  static String capitalize(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }
  
  static String capitalizeWords(String text) {
    return text.split(' ').map((word) => capitalize(word)).join(' ');
  }
  
  static String formatCategoryName(String category) {
    return capitalizeWords(category.replaceAll('_', ' '));
  }
  
  // Color from Status
  static Color getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'active':
      case 'delivered':
      case 'sold':
        return Colors.green;
      case 'in_transit':
      case 'shipped':
        return Colors.blue;
      case 'pending':
      case 'booked':
        return Colors.orange;
      case 'delayed':
      case 'error':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }
  
  // Validation
  static bool isValidEmail(String email) {
    return RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$').hasMatch(email);
  }
  
  static bool isValidPhoneNumber(String phone) {
    return RegExp(r'^\+?[1-9]\d{1,14}$').hasMatch(phone);
  }
  
  // File Size
  static String formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1048576) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / 1048576).toStringAsFixed(1)} MB';
  }
}