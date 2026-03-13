// lib/domain/usecases/auth/logout_usecase.dart
import '../../repositories/auth_repository_interface.dart';

class LogoutUseCase {
  final AuthRepository repository;

  LogoutUseCase(this.repository);

  Future<void> call() async {
    await repository.logout();
  }
}