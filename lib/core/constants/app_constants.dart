// lib/core/constants/app_constants.dart
class AppConstants {
  // App Info
  static const String appName = 'Import Logistics';
  static const String appVersion = '1.0.0';
  
  // Storage Keys
  static const String tokenKey = 'auth_token';
  static const String userKey = 'user_data';
  static const String themeKey = 'theme_mode';
  static const String offlineDataKey = 'offline_data';
  
  // Pagination
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;
  
  // Timeouts
  static const int connectionTimeout = 30000; // 30 seconds
  static const int receiveTimeout = 30000;
  
  // Cache Duration
  static const Duration cacheDuration = Duration(hours: 1);
  static const Duration shortCacheDuration = Duration(minutes: 15);
  
  // Image
  static const double maxImageSize = 2.0; // MB
  static const int imageQuality = 80;
  
  // Currency Symbols
  static const Map<String, String> currencySymbols = {
    'USD': '\$',
    'EUR': '€',
    'CZK': 'Kč',
    'NGN': '₦',
  };
  
  // Container Types
  static const List<String> containerTypes = ['20ft', '40ft'];
  
  // Item Categories
  static const List<String> itemCategories = [
    'electronics',
    'vehicles',
    'engines',
    'appliances',
    'food_items',
    'laptops',
    'other',
  ];
  
  // Item Conditions
  static const List<String> itemConditions = ['new', 'tokunbo', 'used'];
  
  // User Roles
  static const List<String> userRoles = ['admin', 'manager', 'clerk', 'viewer'];
  
  // Expense Types
  static const List<String> expenseTypes = [
    'loading_fee',
    'shipping_fee',
    'clearing_fee',
    'offloading_fee',
    'warehouse_fee',
    'security_fee',
    'extra_fee',
  ];
}