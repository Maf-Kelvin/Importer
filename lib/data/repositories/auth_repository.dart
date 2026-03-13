// lib/data/repositories/auth_repository.dart
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository_interface.dart';
import '../datasources/remote/auth_remote_datasource.dart';
import '../datasources/local/local_storage.dart';
import '../models/user_model.dart';
import '../../core/network/api_client.dart';

class AuthRepositoryImpl implements AuthRepository {
  final AuthRemoteDataSource remoteDataSource;
  final LocalStorage localStorage;

  AuthRepositoryImpl({
    required this.remoteDataSource,
    required this.localStorage,
  });

  @override
  Future<User> login(String username, String password) async {
    try {
      final response = await remoteDataSource.login(username, password);
      
      // Save token
      await ApiClient.instance.setToken(response.accessToken);
      
      // Save user data locally
      await localStorage.saveUser(response.user);
      
      return response.user.toEntity();
    } catch (e) {
      throw Exception('Login failed: $e');
    }
  }

  @override
  Future<void> logout() async {
    try {
      // Clear token
      await ApiClient.instance.clearToken();
      
      // Clear local user data
      await localStorage.clearUser();
    } catch (e) {
      throw Exception('Logout failed: $e');
    }
  }

  @override
  Future<User?> getCurrentUser() async {
    try {
      // Try to get user from local storage first
      final localUser = await localStorage.getUser();
      if (localUser != null) {
        return localUser.toEntity();
      }

      // If not found locally, fetch from remote
      final remoteUser = await remoteDataSource.getCurrentUser();
      await localStorage.saveUser(remoteUser);
      return remoteUser.toEntity();
    } catch (e) {
      return null;
    }
  }

  @override
  Future<bool> isLoggedIn() async {
    final token = await ApiClient.instance.getToken();
    return token != null;
  }
}