# Flutter Frontend API Integration Documentation

**Version:** 1.0.0  
**Framework:** Flutter  
**State Management:** Riverpod  
**HTTP Client:** Dio  

## 📋 Table of Contents

- [API Client Setup](#api-client-setup)
- [Authentication Flow](#authentication-flow)
- [Data Models](#data-models)
- [Repository Pattern](#repository-pattern)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [Offline Support](#offline-support)
- [API Usage Examples](#api-usage-examples)
- [Testing](#testing)

## 🔧 API Client Setup

### Core API Client Configuration

```dart
// lib/core/network/api_client.dart
class ApiClient {
  static ApiClient? _instance;
  static ApiClient get instance => _instance ??= ApiClient._internal();

  late Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiClient._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConstants.baseUrl, // http://localhost:8000/api/v1
      connectTimeout: const Duration(milliseconds: 30000),
      receiveTimeout: const Duration(milliseconds: 30000),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    // Add interceptors for auth, logging, and error handling
    _dio.interceptors.add(AuthInterceptor(_storage));
    _dio.interceptors.add(LoggingInterceptor());
    _dio.interceptors.add(ErrorInterceptor());
  }

  Dio get dio => _dio;
}
```

### Environment Configuration

```dart
// lib/core/constants/api_constants.dart
class ApiConstants {
  // Environment-based configuration
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  // Authentication
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  
  // Containers
  static const String containers = '/containers';
  static String containerById(int id) => '/containers/$id';
  static String sealContainer(int id) => '/containers/$id/seal';
  static String allocateCosts(int id) => '/containers/$id/allocate-costs';
  
  // Items
  static const String items = '/items';
  static String itemById(int id) => '/items/$id';
  static String markSold(int id) => '/items/$id/mark-sold';
  
  // Pricing
  static String generatePricing(int id) => '/pricing/generate/$id';
  static String itemPricing(int id) => '/pricing/item/$id';
}
```

---

## 🔐 Authentication Flow

### Authentication State Management

```dart
// lib/presentation/providers/auth_provider.dart
enum AuthStatus { initial, authenticated, unauthenticated, loading }

class AuthState {
  final AuthStatus status;
  final User? user;
  final String? error;

  const AuthState({
    required this.status,
    this.user,
    this.error,
  });
}

class AuthNotifier extends StateNotifier<AuthState> {
  final LoginUseCase _loginUseCase;
  final LogoutUseCase _logoutUseCase;

  AuthNotifier(this._loginUseCase, this._logoutUseCase) 
      : super(const AuthState(status: AuthStatus.initial));

  Future<void> login(String username, String password) async {
    state = state.copyWith(status: AuthStatus.loading);
    
    try {
      final user = await _loginUseCase(username, password);
      state = state.copyWith(
        status: AuthStatus.authenticated,
        user: user,
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        error: e.toString(),
      );
      rethrow;
    }
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(sl<LoginUseCase>(), sl<LogoutUseCase>());
});
```

### Login Implementation

```dart
// lib/presentation/screens/auth/login_screen.dart
class LoginScreen extends ConsumerStatefulWidget {
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  Future<void> _handleLogin() async {
    try {
      await ref.read(authProvider.notifier).login(
        _usernameController.text.trim(),
        _passwordController.text,
      );
    } catch (e) {
      // Show error message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    
    // Navigate to dashboard when authenticated
    ref.listen(authProvider, (previous, next) {
      if (next.status == AuthStatus.authenticated) {
        context.go('/dashboard');
      }
    });

    return Scaffold(
      body: Form(
        child: Column(
          children: [
            TextFormField(
              controller: _usernameController,
              decoration: InputDecoration(labelText: 'Username'),
            ),
            TextFormField(
              controller: _passwordController,
              decoration: InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            ElevatedButton(
              onPressed: authState.status == AuthStatus.loading 
                  ? null 
                  : _handleLogin,
              child: Text('Sign In'),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 📊 Data Models

### Model Generation with JSON Serialization

```dart
// lib/data/models/container_model.dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/container.dart';

part 'container_model.g.dart';

@JsonSerializable()
class ContainerModel extends Container {
  const ContainerModel({
    required super.id,
    required super.name,
    required super.containerType,
    super.mscContainerNumber,
    required super.allocationMethod,
    required super.ownerId,
    required super.isSealed,
    required super.isShipped,
    required super.createdAt,
    required super.updatedAt,
  });

  factory ContainerModel.fromJson(Map<String, dynamic> json) =>
      _$ContainerModelFromJson(json);

  Map<String, dynamic> toJson() => _$ContainerModelToJson(this);

  Container toEntity() => Container(
    id: id,
    name: name,
    containerType: containerType,
    mscContainerNumber: mscContainerNumber,
    allocationMethod: allocationMethod,
    ownerId: ownerId,
    isSealed: isSealed,
    isShipped: isShipped,
    createdAt: createdAt,
    updatedAt: updatedAt,
  );
}
```

### Request Models

```dart
// lib/data/models/requests/create_container_request.dart
@JsonSerializable()
class CreateContainerRequest {
  final String name;
  
  @JsonKey(name: 'container_type')
  final String containerType;
  
  @JsonKey(name: 'msc_container_number')
  final String? mscContainerNumber;
  
  @JsonKey(name: 'allocation_method')
  final String allocationMethod;
  
  final String? notes;

  const CreateContainerRequest({
    required this.name,
    required this.containerType,
    this.mscContainerNumber,
    this.allocationMethod = 'weight_based',
    this.notes,
  });

  factory CreateContainerRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateContainerRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CreateContainerRequestToJson(this);
}
```

---

## 🏗️ Repository Pattern

### Repository Implementation

```dart
// lib/data/repositories/container_repository.dart
class ContainerRepositoryImpl implements ContainerRepository {
  final ContainerRemoteDataSource remoteDataSource;
  final LocalStorage localStorage;

  ContainerRepositoryImpl({
    required this.remoteDataSource,
    required this.localStorage,
  });

  @override
  Future<PaginatedResponse<Container>> getContainers({
    int skip = 0,
    int limit = 50,
    Map<String, dynamic>? filters,
  }) async {
    try {
      // Try to get from remote first
      final response = await remoteDataSource.getContainers(
        skip: skip,
        limit: limit,
        filters: filters,
      );
      
      // Cache the data locally
      await _cacheContainers(response.items);
      
      return PaginatedResponse(
        items: response.items.map((model) => model.toEntity()).toList(),
        total: response.total,
        page: response.page,
        perPage: response.perPage,
        pages: response.pages,
      );
    } catch (e) {
      // Fallback to local data if network fails
      final localContainers = await localStorage.getContainers();
      return PaginatedResponse(
        items: localContainers,
        total: localContainers.length,
        page: 1,
        perPage: localContainers.length,
        pages: 1,
      );
    }
  }

  @override
  Future<Container> createContainer(CreateContainerRequest request) async {
    try {
      final containerModel = await remoteDataSource.createContainer(request);
      final container = containerModel.toEntity();
      
      // Cache locally
      await localStorage.saveContainer(containerModel);
      
      return container;
    } catch (e) {
      // Queue for sync when online
      await localStorage.queueCreateContainer(request);
      rethrow;
    }
  }

  Future<void> _cacheContainers(List<ContainerModel> containers) async {
    for (final container in containers) {
      await localStorage.saveContainer(container);
    }
  }
}
```

### Remote Data Source

```dart
// lib/data/datasources/remote/container_remote_datasource.dart
abstract class ContainerRemoteDataSource {
  Future<PaginatedResponseModel<ContainerModel>> getContainers({
    int skip = 0,
    int limit = 50,
    Map<String, dynamic>? filters,
  });

  Future<ContainerModel> createContainer(CreateContainerRequest request);
  Future<ContainerModel> getContainer(int id);
  Future<ContainerModel> updateContainer(int id, UpdateContainerRequest request);
  Future<void> deleteContainer(int id);
}

class ContainerRemoteDataSourceImpl implements ContainerRemoteDataSource {
  final ApiClient apiClient;

  ContainerRemoteDataSourceImpl(this.apiClient);

  @override
  Future<PaginatedResponseModel<ContainerModel>> getContainers({
    int skip = 0,
    int limit = 50,
    Map<String, dynamic>? filters,
  }) async {
    final queryParameters = {
      'skip': skip,
      'limit': limit,
      if (filters != null) ...filters,
    };

    final response = await apiClient.get(
      ApiConstants.containers,
      queryParameters: queryParameters,
    );

    return PaginatedResponseModel<ContainerModel>.fromJson(
      response.data,
      (json) => ContainerModel.fromJson(json as Map<String, dynamic>),
    );
  }

  @override
  Future<ContainerModel> createContainer(CreateContainerRequest request) async {
    final response = await apiClient.post(
      ApiConstants.containers,
      data: request.toJson(),
    );

    return ContainerModel.fromJson(response.data);
  }
}
```

---

## 🔄 State Management

### Container Provider

```dart
// lib/presentation/providers/container_provider.dart
class ContainerState {
  final List<Container> containers;
  final bool isLoading;
  final String? error;
  final bool hasMore;
  final int currentPage;

  const ContainerState({
    this.containers = const [],
    this.isLoading = false,
    this.error,
    this.hasMore = true,
    this.currentPage = 0,
  });

  ContainerState copyWith({
    List<Container>? containers,
    bool? isLoading,
    String? error,
    bool? hasMore,
    int? currentPage,
  }) {
    return ContainerState(
      containers: containers ?? this.containers,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      hasMore: hasMore ?? this.hasMore,
      currentPage: currentPage ?? this.currentPage,
    );
  }
}

class ContainerNotifier extends StateNotifier<ContainerState> {
  final GetContainersUseCase _getContainersUseCase;
  final CreateContainerUseCase _createContainerUseCase;

  ContainerNotifier(
    this._getContainersUseCase,
    this._createContainerUseCase,
  ) : super(const ContainerState());

  Future<void> loadContainers({bool refresh = false}) async {
    if (refresh) {
      state = state.copyWith(containers: [], currentPage: 0, hasMore: true);
    }

    if (state.isLoading || !state.hasMore) return;

    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _getContainersUseCase(
        skip: state.currentPage * 20,
        limit: 20,
      );

      final newContainers = refresh 
          ? response.items
          : [...state.containers, ...response.items];

      state = state.copyWith(
        containers: newContainers,
        isLoading: false,
        hasMore: response.items.length == 20,
        currentPage: state.currentPage + 1,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  Future<void> createContainer(CreateContainerRequest request) async {
    try {
      final container = await _createContainerUseCase(request);
      
      state = state.copyWith(
        containers: [container, ...state.containers],
      );
    } catch (e) {
      rethrow;
    }
  }
}

final containerProvider = StateNotifierProvider<ContainerNotifier, ContainerState>((ref) {
  return ContainerNotifier(
    sl<GetContainersUseCase>(),
    sl<CreateContainerUseCase>(),
  );
});
```

### Using Providers in UI

```dart
// lib/presentation/screens/containers/container_list_screen.dart
class ContainerListScreen extends ConsumerStatefulWidget {
  @override
  ConsumerState<ContainerListScreen> createState() => _ContainerListScreenState();
}

class _ContainerListScreenState extends ConsumerState<ContainerListScreen> {
  @override
  void initState() {
    super.initState();
    // Load containers when screen initializes
    Future.microtask(() => ref.read(containerProvider.notifier).loadContainers());
  }

  @override
  Widget build(BuildContext context) {
    final containerState = ref.watch(containerProvider);

    return Scaffold(
      appBar: AppBar(title: Text('Containers')),
      body: RefreshIndicator(
        onRefresh: () => ref.read(containerProvider.notifier).loadContainers(refresh: true),
        child: _buildBody(containerState),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/containers/create'),
        child: Icon(Icons.add),
      ),
    );
  }

  Widget _buildBody(ContainerState state) {
    if (state.isLoading && state.containers.isEmpty) {
      return Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.containers.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: ${state.error}'),
            ElevatedButton(
              onPressed: () => ref.read(containerProvider.notifier).loadContainers(),
              child: Text('Retry'),
            ),
          ],
        ),
      );
    }

    return NotificationListener<ScrollNotification>(
      onNotification: (scrollInfo) {
        if (scrollInfo.metrics.pixels == scrollInfo.metrics.maxScrollExtent) {
          // Load more when reaching bottom
          ref.read(containerProvider.notifier).loadContainers();
        }
        return false;
      },
      child: ListView.builder(
        itemCount: state.containers.length + (state.isLoading ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == state.containers.length) {
            return Center(child: CircularProgressIndicator());
          }

          final container = state.containers[index];
          return ContainerCard(
            container: container,
            onTap: () => context.go('/containers/${container.id}'),
          );
        },
      ),
    );
  }
}
```

---

## ⚠️ Error Handling

### Global Error Handler

```dart
// lib/core/network/interceptors.dart
class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    String message = 'An error occurred';
    
    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
        message = 'Connection timeout. Please check your internet connection.';
        break;
      case DioExceptionType.connectionError:
        message = 'Unable to connect to server. Please try again later.';
        break;
      case DioExceptionType.badResponse:
        message = _handleHttpError(err.response?.statusCode);
        break;
      default:
        message = 'An unexpected error occurred.';
    }

    handler.next(DioException(
      requestOptions: err.requestOptions,
      response: err.response,
      type: err.type,
      message: message,
    ));
  }

  String _handleHttpError(int? statusCode) {
    switch (statusCode) {
      case 400:
        return 'Invalid request. Please check your input.';
      case 401:
        return 'Authentication failed. Please login again.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'Requested resource not found.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return 'An error occurred (${statusCode}). Please try again.';
    }
  }
}
```

### Error State Management

```dart
// lib/presentation/providers/error_provider.dart
class ErrorNotifier extends StateNotifier<String?> {
  ErrorNotifier() : super(null);

  void showError(String message) {
    state = message;
  }

  void clearError() {
    state = null;
  }
}

final errorProvider = StateNotifierProvider<ErrorNotifier, String?>((ref) {
  return ErrorNotifier();
});

// Usage in UI
Consumer(
  builder: (context, ref, child) {
    final error = ref.watch(errorProvider);
    
    ref.listen<String?>(errorProvider, (previous, next) {
      if (next != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next),
            backgroundColor: Colors.red,
            action: SnackBarAction(
              label: 'Dismiss',
              onPressed: () => ref.read(errorProvider.notifier).clearError(),
            ),
          ),
        );
      }
    });

    return YourWidget();
  },
);
```

---

## 💿 Offline Support

### Local Storage Implementation

```dart
// lib/data/datasources/local/local_storage.dart
class LocalStorageImpl implements LocalStorage {
  @override
  Future<void> saveContainer(ContainerModel container) async {
    final box = Hive.box<Map>('containers');
    await box.put(container.id, container.toJson());
  }

  @override
  Future<List<Container>> getContainers() async {
    final box = Hive.box<Map>('containers');
    final containers = <Container>[];
    
    for (final containerData in box.values) {
      try {
        final container = ContainerModel.fromJson(
          Map<String, dynamic>.from(containerData),
        );
        containers.add(container.toEntity());
      } catch (e) {
        // Skip invalid data
        continue;
      }
    }
    
    return containers;
  }

  @override
  Future<void> queueCreateContainer(CreateContainerRequest request) async {
    final box = Hive.box<Map>('pending_actions');
    final actions = box.get('create_containers', defaultValue: <Map>[]);
    
    actions.add({
      'action': 'create_container',
      'data': request.toJson(),
      'timestamp': DateTime.now().toIso8601String(),
    });
    
    await box.put('create_containers', actions);
  }
}
```

### Sync Manager

```dart
// lib/core/sync/sync_manager.dart
class SyncManager {
  final LocalStorage localStorage;
  final ContainerRemoteDataSource remoteDataSource;

  SyncManager(this.localStorage, this.remoteDataSource);

  Future<void> syncPendingActions() async {
    try {
      await _syncPendingContainers();
      await _syncPendingItems();
      // Clear synced actions
      await _clearSyncedActions();
    } catch (e) {
      // Log error, will retry next time
      print('Sync failed: $e');
    }
  }

  Future<void> _syncPendingContainers() async {
    final pendingContainers = await localStorage.getPendingCreateContainers();
    
    for (final request in pendingContainers) {
      try {
        await remoteDataSource.createContainer(request);
      } catch (e) {
        // Skip this one, will retry next sync
        continue;
      }
    }
  }
}

// Auto-sync when network is available
class NetworkAwareSyncManager {
  final SyncManager syncManager;
  StreamSubscription<ConnectivityResult>? _connectivity;

  NetworkAwareSyncManager(this.syncManager) {
    _connectivity = Connectivity().onConnectivityChanged.listen((result) {
      if (result != ConnectivityResult.none) {
        syncManager.syncPendingActions();
      }
    });
  }

  void dispose() {
    _connectivity?.cancel();
  }
}
```

---

## 📱 API Usage Examples

### Container Management

```dart
// Create Container
final createRequest = CreateContainerRequest(
  name: 'CONT-2024-001',
  containerType: '40ft',
  mscContainerNumber: 'MSCU123456789',
  allocationMethod: 'weight_based',
  notes: 'Electronics shipment',
);

try {
  await ref.read(containerProvider.notifier).createContainer(createRequest);
  // Success feedback
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Container created successfully!')),
  );
} catch (e) {
  // Error handling
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Failed to create container: $e')),
  );
}
```

### Item Management

```dart
// Add Item to Container
final itemRequest = CreateItemRequest(
  containerId: containerId,
  name: 'Samsung 55" QLED TV',
  description: '4K Smart TV with HDR',
  category: 'electronics',
  condition: 'new',
  purchasePrice: 800.0,
  purchaseCurrency: 'USD',
  weight: 25.5,
  volume: 0.15,
);

try {
  final item = await ref.read(itemProvider.notifier).createItem(itemRequest);
  // Navigate to item details
  context.go('/items/${item.id}');
} catch (e) {
  // Show error
}
```

### Pricing Integration

```dart
// Generate Pricing Recommendations
final pricingRequest = PricingRequest(
  includeCostBased: true,
  includeMarketPricing: true,
  includeLastSold: true,
  profitMargin: 0.25,
  sources: ['jiji', 'ebay'],
);

try {
  final pricing = await ref.read(pricingProvider.notifier)
      .generatePricing(itemId, pricingRequest);
  
  // Display pricing recommendations
  showDialog(
    context: context,
    builder: (context) => PricingDialog(pricing: pricing),
  );
} catch (e) {
  // Handle error
}
```

### Real-time Updates

```dart
// Listen for container status updates
ref.listen<ContainerState>(containerProvider, (previous, next) {
  if (previous?.containers.length != next.containers.length) {
    // New container added
    _showUpdateNotification('New container added!');
  }
});

// WebSocket integration (future feature)
class TrackingWebSocket {
  late WebSocketChannel channel;

  void connect() {
    channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8000/ws/tracking'),
    );

    channel.stream.listen((data) {
      final update = jsonDecode(data);
      // Update container tracking state
      ref.read(trackingProvider.notifier).updateFromWebSocket(update);
    });
  }
}
```

---

## 🧪 Testing

### Unit Testing Data Sources

```dart
// test/data/datasources/container_remote_datasource_test.dart
void main() {
  group('ContainerRemoteDataSource', () {
    late MockApiClient mockApiClient;
    late ContainerRemoteDataSourceImpl dataSource;

    setUp(() {
      mockApiClient = MockApiClient();
      dataSource = ContainerRemoteDataSourceImpl(mockApiClient);
    });

    test('should return containers when API call is successful', () async {
      // Arrange
      final responseData = {
        'items': [
          {'id': 1, 'name': 'CONT-001', 'container_type': '40ft'}
        ],
        'total': 1,
        'page': 1,
        'per_page': 50,
        'pages': 1,
      };

      when(mockApiClient.get(any, queryParameters: anyNamed('queryParameters')))
          .thenAnswer((_) async => Response(
                data: responseData,
                statusCode: 200,
                requestOptions: RequestOptions(path: ''),
              ));

      // Act
      final result = await dataSource.getContainers();

      // Assert
      expect(result.items.length, 1);
      expect(result.items.first.name, 'CONT-001');
      verify(mockApiClient.get(ApiConstants.containers, queryParameters: anyNamed('queryParameters')));
    });

    test('should throw exception when API call fails', () async {
      // Arrange
      when(mockApiClient.get(any, queryParameters: anyNamed('queryParameters')))
          .thenThrow(DioException(
            requestOptions: RequestOptions(path: ''),
            message: 'Network error',
          ));

      // Act & Assert
      expect(() => dataSource.getContainers(), throwsException);
    });
  });
}
```

### Widget Testing

```dart
// test/presentation/screens/login_screen_test.dart
void main() {
  group('LoginScreen', () {
    testWidgets('should show login form', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(home: LoginScreen()),
        ),
      );

      expect(find.byType(TextFormField), findsNWidgets(2));
      expect(find.text('Sign In'), findsOneWidget);
    });

    testWidgets('should call login when button pressed', (tester) async {
      final mockAuthNotifier = MockAuthNotifier();
      
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authProvider.overrideWith(() => mockAuthNotifier),
          ],
          child: MaterialApp(home: LoginScreen()),
        ),
      );

      await tester.enterText(find.byType(TextFormField).first, 'admin');
      await tester.enterText(find.byType(TextFormField).last, 'password');
      await tester.tap(find.text('Sign In'));
      await tester.pump();

      verify(mockAuthNotifier.login('admin', 'password')).called(1);
    });
  });
}
```

### Integration Testing

```dart
// integration_test/app_test.dart
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('App Integration Test', () {
    testWidgets('complete login flow', (tester) async {
      await tester.pumpWidget(ImportLogisticsApp());
      await tester.pumpAndSettle();

      // Should show login screen
      expect(find.text('Sign In'), findsOneWidget);

      // Enter credentials
      await tester.enterText(find.byKey(Key('username_field')), 'admin');
      await tester.enterText(find.byKey(Key('password_field')), 'changethis');

      // Tap login
      await tester.tap(find.text('Sign In'));
      await tester.pumpAndSettle();

      // Should navigate to dashboard
      expect(find.text('Welcome'), findsOneWidget);
    });
  });
}
```

---

## 🚀 Performance Optimization

### Image Caching

```dart
// lib/presentation/widgets/cached_image.dart
class CachedImage extends StatelessWidget {
  final String imageUrl;
  final double? width;
  final double? height;

  const CachedImage({
    Key? key,
    required this.imageUrl,
    this.width,
    this.height,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return CachedNetworkImage(
      imageUrl: imageUrl,
      width: width,
      height: height,
      placeholder: (context, url) => Shimmer.fromColors(
        baseColor: Colors.grey[300]!,
        highlightColor: Colors.grey[100]!,
        child: Container(
          width: width,
          height: height,
          color: Colors.white,
        ),
      ),
      errorWidget: (context, url, error) => Icon(Icons.error),
      memCacheWidth: width?.toInt(),
      memCacheHeight: height?.toInt(),
    );
  }
}
```

### Pagination and Lazy Loading

```dart
// lib/presentation/widgets/infinite_scroll_list.dart
class InfiniteScrollList<T> extends StatefulWidget {
  final Future<void> Function() onLoadMore;
  final List<T> items;
  final Widget Function(T item) itemBuilder;
  final bool hasMore;
  final bool isLoading;

  const InfiniteScrollList({
    Key? key,
    required this.onLoadMore,
    required this.items,
    required this.itemBuilder,
    required this.hasMore,
    required this.isLoading,
  }) : super(key: key);

  @override
  State<InfiniteScrollList<T>> createState() => _InfiniteScrollListState<T>();
}

class _InfiniteScrollListState<T> extends State<InfiniteScrollList<T>> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels ==
        _scrollController.position.maxScrollExtent &&
        widget.hasMore &&
        !widget.isLoading) {
      widget.onLoadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      controller: _scrollController,
      itemCount: widget.items.length + (widget.isLoading ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == widget.items.length) {
          return Center(child: CircularProgressIndicator());
        }
        return widget.itemBuilder(widget.items[index]);
      },
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }
}
```

---

## 📝 Best Practices

### 1. **Consistent Error Handling**
```dart
// Use consistent error handling across all API calls
try {
  final result = await apiCall();
  return Success(result);
} on DioException catch (e) {
  return Failure(ApiException.fromDioException(e));
} catch (e) {
  return Failure(UnknownException(e.toString()));
}
```

### 2. **Proper State Management**
```dart
// Always use copyWith for state updates
state = state.copyWith(
  isLoading: false,
  data: newData,
  error: null, // Clear previous errors
);
```

### 3. **Resource Management**
```dart
// Always dispose of controllers and subscriptions
@override
void dispose() {
  _controller.dispose();
  _subscription?.cancel();
  super.dispose();
}
```

### 4. **Network Awareness**
```dart
// Check connectivity before making API calls
final connectivity = await Connectivity().checkConnectivity();
if (connectivity == ConnectivityResult.none) {
  throw NoInternetException();
}
```

### 5. **Caching Strategy**
```dart
// Implement smart caching
if (shouldUseCache(lastFetch)) {
  return await localStorage.getData();
} else {
  final data = await remoteDataSource.getData();
  await localStorage.saveData(data);
  return data;
}
```

---

This comprehensive documentation provides everything needed to integrate the Flutter frontend with your FastAPI backend, ensuring robust, scalable, and maintainable code architecture!