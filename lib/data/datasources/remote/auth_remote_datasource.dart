// lib/data/datasources/remote/auth_remote_datasource.dart
import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';
import '../../../core/constants/api_constants.dart';
import '../../models/user_model.dart';

abstract class AuthRemoteDataSource {
  Future<LoginResponse> login(String username, String password);
  Future<UserModel> register(Map<String, dynamic> userData);
  Future<UserModel> getCurrentUser();
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  final ApiClient apiClient;

  AuthRemoteDataSourceImpl(this.apiClient);

  @override
  Future<LoginResponse> login(String username, String password) async {
    try {
      final response = await apiClient.login({
        'username': username,
        'password': password,
      });

      return LoginResponse.fromJson(response.data);
    } catch (e) {
      throw Exception('Login failed: $e');
    }
  }

  @override
  Future<UserModel> register(Map<String, dynamic> userData) async {
    try {
      final response = await apiClient.post(ApiConstants.register, data: userData);
      return UserModel.fromJson(response.data);
    } catch (e) {
      throw Exception('Registration failed: $e');
    }
  }

  @override
  Future<UserModel> getCurrentUser() async {
    try {
      final response = await apiClient.get(ApiConstants.profile);
      return UserModel.fromJson(response.data);
    } catch (e) {
      throw Exception('Failed to get user profile: $e');
    }
  }
}