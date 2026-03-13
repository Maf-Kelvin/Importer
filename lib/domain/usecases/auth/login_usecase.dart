// lib/domain/usecases/auth/login_usecase.dart
import '../../entities/user.dart';
import '../../repositories/auth_repository_interface.dart';

class LoginUseCase {
  final AuthRepository repository;

  LoginUseCase(this.repository);

  Future<User> call(String username, String password) async {
    if (username.isEmpty || password.isEmpty) {
      throw Exception('Username and password are required');
    }
    
    return await repository.login(username, password);
  }
}