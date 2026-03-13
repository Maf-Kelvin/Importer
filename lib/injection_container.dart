// lib/injection_container.dart
import 'package:get_it/get_it.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';

// Core
import 'core/network/api_client.dart';

// Data sources
import 'data/datasources/remote/auth_remote_datasource.dart';
import 'data/datasources/remote/container_remote_datasource.dart';
import 'data/datasources/local/local_storage.dart';

// Repositories
import 'data/repositories/auth_repository.dart';
import 'data/repositories/container_repository.dart';

// Use cases
import 'domain/usecases/auth/login_usecase.dart';
import 'domain/usecases/auth/logout_usecase.dart';
import 'domain/usecases/containers/create_container_usecase.dart';
import 'domain/usecases/containers/get_containers_usecase.dart';

final sl = GetIt.instance;

Future<void> init() async {
  // External
  final sharedPreferences = await SharedPreferences.getInstance();
  sl.registerLazySingleton(() => sharedPreferences);
  sl.registerLazySingleton(() => const FlutterSecureStorage());
  
  // Initialize Hive boxes
  await Hive.openBox('containers');
  await Hive.openBox('items');
  await Hive.openBox('user_data');

  // Core
  sl.registerLazySingleton(() => ApiClient.instance);

  // Data sources
  sl.registerLazySingleton<AuthRemoteDataSource>(
    () => AuthRemoteDataSourceImpl(sl()),
  );
  sl.registerLazySingleton<ContainerRemoteDataSource>(
    () => ContainerRemoteDataSourceImpl(sl()),
  );
  sl.registerLazySingleton<LocalStorage>(
    () => LocalStorageImpl(),
  );

  // Repositories
  sl.registerLazySingleton<AuthRepository>(
    () => AuthRepositoryImpl(
      remoteDataSource: sl(),
      localStorage: sl(),
    ),
  );
  sl.registerLazySingleton<ContainerRepository>(
    () => ContainerRepositoryImpl(
      remoteDataSource: sl(),
      localStorage: sl(),
    ),
  );

  // Use cases
  sl.registerLazySingleton(() => LoginUseCase(sl()));
  sl.registerLazySingleton(() => LogoutUseCase(sl()));
  sl.registerLazySingleton(() => CreateContainerUseCase(sl()));
  sl.registerLazySingleton(() => GetContainersUseCase(sl()));
}