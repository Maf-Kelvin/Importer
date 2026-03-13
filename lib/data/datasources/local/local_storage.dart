// lib/data/datasources/local/local_storage.dart
import 'package:hive/hive.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/constants/app_constants.dart';
import '../../models/user_model.dart';

abstract class LocalStorage {
  Future<void> saveUser(UserModel user);
  Future<UserModel?> getUser();
  Future<void> clearUser();
  Future<void> saveOfflineData(String key, dynamic data);
  Future<T?> getOfflineData<T>(String key);
  Future<void> clearOfflineData(String key);
}

class LocalStorageImpl implements LocalStorage {
  @override
  Future<void> saveUser(UserModel user) async {
    final box = Hive.box('user_data');
    await box.put(AppConstants.userKey, user.toJson());
  }

  @override
  Future<UserModel?> getUser() async {
    try {
      final box = Hive.box('user_data');
      final userData = box.get(AppConstants.userKey);
      if (userData != null) {
        return UserModel.fromJson(Map<String, dynamic>.from(userData));
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  @override
  Future<void> clearUser() async {
    final box = Hive.box('user_data');
    await box.delete(AppConstants.userKey);
  }

  @override
  Future<void> saveOfflineData(String key, dynamic data) async {
    final prefs = await SharedPreferences.getInstance();
    if (data is String) {
      await prefs.setString(key, data);
    } else if (data is bool) {
      await prefs.setBool(key, data);
    } else if (data is int) {
      await prefs.setInt(key, data);
    } else if (data is double) {
      await prefs.setDouble(key, data);
    } else if (data is List<String>) {
      await prefs.setStringList(key, data);
    }
  }

  @override
  Future<T?> getOfflineData<T>(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.get(key) as T?;
  }

  @override
  Future<void> clearOfflineData(String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }
}