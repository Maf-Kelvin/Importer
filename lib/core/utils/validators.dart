// lib/core/utils/validators.dart
class Validators {
  static String? required(String? value, [String? fieldName]) {
    if (value == null || value.trim().isEmpty) {
      return '${fieldName ?? 'Field'} is required';
    }
    return null;
  }
  
  static String? email(String? value) {
    if (value == null || value.isEmpty) return 'Email is required';
    if (!value.isValidEmail) return 'Enter a valid email address';
    return null;
  }
  
  static String? minLength(String? value, int minLength, [String? fieldName]) {
    if (value == null || value.length < minLength) {
      return '${fieldName ?? 'Field'} must be at least $minLength characters';
    }
    return null;
  }
  
  static String? maxLength(String? value, int maxLength, [String? fieldName]) {
    if (value != null && value.length > maxLength) {
      return '${fieldName ?? 'Field'} must be less than $maxLength characters';
    }
    return null;
  }
  
  static String? positiveNumber(String? value, [String? fieldName]) {
    if (value == null || value.isEmpty) {
      return '${fieldName ?? 'Field'} is required';
    }
    final number = double.tryParse(value);
    if (number == null || number <= 0) {
      return '${fieldName ?? 'Field'} must be a positive number';
    }
    return null;
  }
  
  static String? currency(String? value) {
    if (value == null || value.isEmpty) return 'Currency is required';
    if (!AppConstants.currencySymbols.containsKey(value)) {
      return 'Invalid currency';
    }
    return null;
  }
  
  static String? phoneNumber(String? value) {
    if (value == null || value.isEmpty) return 'Phone number is required';
    if (!value.isValidPhoneNumber) return 'Enter a valid phone number';
    return null;
  }
  
  static String? password(String? value) {
    if (value == null || value.isEmpty) return 'Password is required';
    if (value.length < 6) return 'Password must be at least 6 characters';
    return null;
  }
  
  static String? confirmPassword(String? value, String? password) {
    if (value == null || value.isEmpty) return 'Confirm password is required';
    if (value != password) return 'Passwords do not match';
    return null;
  }
}