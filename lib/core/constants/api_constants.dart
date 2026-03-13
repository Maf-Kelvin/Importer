// lib/core/constants/api_constants.dart
class ApiConstants {
  // Base URL
  static const String baseUrl = 'http://localhost:8000/api/v1';
  
  // Auth Endpoints
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String refresh = '/auth/refresh';
  
  // User Endpoints
  static const String users = '/users';
  static const String profile = '/users/me';
  
  // Container Endpoints
  static const String containers = '/containers';
  static String containerById(int id) => '/containers/$id';
  static String sealContainer(int id) => '/containers/$id/seal';
  static String allocateCosts(int id) => '/containers/$id/allocate-costs';
  
  // Item Endpoints
  static const String items = '/items';
  static String itemById(int id) => '/items/$id';
  static String markSold(int id) => '/items/$id/mark-sold';
  
  // Expense Endpoints
  static const String expenses = '/expenses';
  static String containerExpenses(int id) => '/expenses/container/$id';
  
  // Pricing Endpoints
  static const String pricing = '/pricing';
  static String generatePricing(int id) => '/pricing/generate/$id';
  static String itemPricing(int id) => '/pricing/item/$id';
  static String refreshMarket(int id) => '/pricing/refresh-market/$id';
  
  // Tracking Endpoints
  static const String tracking = '/tracking';
  static String updateTracking(int id) => '/tracking/$id/update';
  static String trackingHistory(int id) => '/tracking/$id/history';
  static String trackingStatus(int id) => '/tracking/$id/status';
  
  // Reports Endpoints
  static const String reports = '/reports';
  static const String profitItems = '/reports/profit/items';
  static const String profitContainers = '/reports/profit/containers';
  static const String profitCategories = '/reports/profit/categories';
}