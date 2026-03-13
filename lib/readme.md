# Import Profit & Logistics Intelligence System - Flutter Frontend

A comprehensive Flutter application for managing import containers, tracking shipments, calculating costs, and optimizing pricing strategies. This mobile and desktop app works seamlessly with the FastAPI backend to provide a complete logistics management solution.

## 📱 Screenshots & Features

### Mobile-First Design
- **Dashboard**: Real-time metrics, quick actions, and activity timeline
- **Container Management**: Create, track, and manage 20ft/40ft containers  
- **Item Catalog**: Add items with photos, weights, and pricing
- **Reports & Analytics**: Visual profit analysis and performance metrics
- **Offline Support**: Work offline and sync when connected

### Cross-Platform Support
- **📱 Mobile**: iOS and Android native performance
- **💻 Desktop**: Windows, macOS, and Linux support
- **🌐 Web**: Progressive Web App capabilities
- **📱 Tablet**: Optimized layouts for larger screens

## 🏗️ Architecture

```
Clean Architecture + MVVM Pattern
├── 📱 Presentation Layer (UI/Widgets/Screens)
├── 🔄 State Management (Riverpod Providers)
├── 🏢 Domain Layer (Entities/Use Cases)
├── 💾 Data Layer (Repositories/Data Sources)
├── 🌐 Network Layer (API Client/Interceptors)
└── 💿 Local Storage (Hive/Secure Storage)
```

## 📁 Project Structure

```
lib/
├── main.dart                           # App entry point
├── app.dart                           # Main app configuration
├── injection_container.dart           # Dependency injection setup
├── core/                             # Core utilities and configuration
│   ├── constants/
│   │   ├── app_constants.dart        # Application constants
│   │   ├── api_constants.dart        # API endpoints and configuration
│   │   └── theme_constants.dart      # Theme-related constants
│   ├── utils/
│   │   ├── helpers.dart              # Utility functions and formatters
│   │   ├── validators.dart           # Form validation logic
│   │   ├── extensions.dart           # Dart extensions
│   │   └── responsive.dart           # Responsive design utilities
│   ├── errors/
│   │   ├── exceptions.dart           # Custom exceptions
│   │   └── failures.dart             # Error handling
│   └── network/
│       ├── api_client.dart           # HTTP client configuration
│       ├── interceptors.dart         # Request/response interceptors
│       └── network_info.dart         # Network connectivity
├── data/                             # Data layer implementation
│   ├── models/                       # JSON serializable data models
│   │   ├── user_model.dart           # User data model
│   │   ├── container_model.dart      # Container data model
│   │   ├── item_model.dart           # Item data model
│   │   ├── expense_model.dart        # Expense data model
│   │   ├── pricing_model.dart        # Pricing data model
│   │   └── tracking_model.dart       # Tracking data model
│   ├── repositories/                 # Repository implementations
│   │   ├── auth_repository.dart      # Authentication repository
│   │   ├── container_repository.dart # Container repository
│   │   ├── item_repository.dart      # Item repository
│   │   ├── pricing_repository.dart   # Pricing repository
│   │   └── tracking_repository.dart  # Tracking repository
│   └── datasources/                  # Data source abstractions
│       ├── local/                    # Local storage
│       │   ├── local_storage.dart    # Local storage interface
│       │   └── hive_helper.dart      # Hive database helper
│       └── remote/                   # Remote API
│           ├── auth_remote_datasource.dart    # Auth API calls
│           ├── container_remote_datasource.dart # Container API calls
│           └── api_endpoints.dart              # API endpoint definitions
├── domain/                           # Business logic layer
│   ├── entities/                     # Business entities
│   │   ├── user.dart                 # User entity
│   │   ├── container.dart            # Container entity
│   │   ├── item.dart                 # Item entity
│   │   ├── expense.dart              # Expense entity
│   │   └── pricing.dart              # Pricing entity
│   ├── usecases/                     # Business use cases
│   │   ├── auth/                     # Authentication use cases
│   │   │   ├── login_usecase.dart    # Login logic
│   │   │   └── logout_usecase.dart   # Logout logic
│   │   ├── containers/               # Container use cases
│   │   │   ├── create_container_usecase.dart  # Create container logic
│   │   │   └── get_containers_usecase.dart    # Get containers logic
│   │   └── items/                    # Item use cases
│   │       ├── add_item_usecase.dart         # Add item logic
│   │       └── calculate_pricing_usecase.dart # Pricing calculation
│   └── repositories/                 # Repository interfaces
│       ├── auth_repository_interface.dart      # Auth repository contract
│       └── container_repository_interface.dart # Container repository contract
├── presentation/                     # UI layer
│   ├── providers/                    # State management providers
│   │   ├── auth_provider.dart        # Authentication state
│   │   ├── container_provider.dart   # Container state
│   │   ├── item_provider.dart        # Item state
│   │   └── theme_provider.dart       # Theme state
│   ├── screens/                      # Application screens
│   │   ├── auth/                     # Authentication screens
│   │   │   ├── login_screen.dart     # Login screen
│   │   │   └── splash_screen.dart    # Splash screen
│   │   ├── dashboard/                # Dashboard screens
│   │   │   ├── dashboard_screen.dart # Main dashboard
│   │   │   └── widgets/              # Dashboard-specific widgets
│   │   │       ├── metric_card.dart  # Metric display cards
│   │   │       └── recent_activity.dart # Activity timeline
│   │   ├── containers/               # Container management screens
│   │   │   ├── container_list_screen.dart   # Container list view
│   │   │   ├── container_detail_screen.dart # Container details
│   │   │   ├── create_container_screen.dart # Create new container
│   │   │   └── widgets/              # Container-specific widgets
│   │   │       ├── container_card.dart      # Container display card
│   │   │       └── cost_allocation_dialog.dart # Cost allocation UI
│   │   ├── items/                    # Item management screens
│   │   │   ├── item_list_screen.dart # Item list view
│   │   │   ├── item_detail_screen.dart # Item details
│   │   │   ├── add_item_screen.dart  # Add new item
│   │   │   └── widgets/              # Item-specific widgets
│   │   │       ├── item_card.dart    # Item display card
│   │   │       └── pricing_widget.dart # Pricing display
│   │   ├── reports/                  # Reports and analytics
│   │   │   ├── reports_screen.dart   # Reports dashboard
│   │   │   └── widgets/              # Report-specific widgets
│   │   │       ├── profit_chart.dart # Profit visualization
│   │   │       └── category_breakdown.dart # Category analysis
│   │   └── settings/                 # Settings and preferences
│   │       ├── settings_screen.dart  # Settings menu
│   │       └── profile_screen.dart   # User profile
│   ├── widgets/                      # Reusable UI components
│   │   ├── common/                   # Common widgets
│   │   │   ├── custom_button.dart    # Styled buttons
│   │   │   ├── custom_text_field.dart # Styled text inputs
│   │   │   ├── loading_widget.dart   # Loading indicators
│   │   │   └── error_widget.dart     # Error displays
│   │   ├── navigation/               # Navigation components
│   │   │   ├── bottom_nav_bar.dart   # Bottom navigation
│   │   │   └── drawer_menu.dart      # Side drawer menu
│   │   └── charts/                   # Chart components
│   │       ├── profit_chart.dart     # Profit visualization
│   │       └── currency_impact_chart.dart # FX impact charts
│   ├── routes/                       # Navigation routing
│   │   ├── app_router.dart          # Main router configuration
│   │   └── route_names.dart         # Route name constants
│   └── themes/                       # Application theming
│       ├── app_theme.dart           # Main theme configuration
│       ├── light_theme.dart         # Light theme definition
│       └── dark_theme.dart          # Dark theme definition
```

## 🚀 Features

### 📊 Dashboard & Analytics
- **Real-time Metrics**: Active containers, total items, revenue, profit margins
- **Quick Actions**: Fast access to create containers and add items
- **Activity Timeline**: Recent actions and status updates
- **Role-based Content**: UI adapts to user permissions

### 📦 Container Management
- **Container CRUD**: Create, view, edit, and manage containers
- **Type Support**: 20ft and 40ft container types
- **MSC Integration**: Track containers with MSC numbers
- **Cost Allocation**: Weight-based or value-based cost distribution
- **Status Tracking**: Visual progress indicators and completion status

### 📋 Item Management
- **Item Catalog**: Comprehensive item management system
- **Categories**: Electronics, vehicles, engines, appliances, food, laptops
- **Condition Tracking**: New, tokunbo (used), and used items
- **Multi-Currency**: Support for USD, EUR, CZK, NGN
- **Weight & Volume**: Physical property tracking

### 💰 Pricing Intelligence
- **Cost-Based Pricing**: Landed cost + configurable margins
- **Market Price Integration**: Web scraping from multiple sources
- **Price History**: Historical pricing data and trends
- **Profit Calculations**: Real-time profit margin analysis

### 🚚 Tracking & Logistics
- **MSC Integration**: Real-time shipment tracking
- **Status Updates**: Container location and status monitoring
- **Notification System**: Automated alerts for status changes
- **Timeline View**: Complete tracking history

### 🔐 Authentication & Security
- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access**: Admin, Manager, Clerk, Viewer roles
- **Secure Storage**: Encrypted local storage for sensitive data
- **Auto Session Management**: Automatic token refresh and logout

### 📱 Mobile-First Experience
- **Responsive Design**: Optimized for all screen sizes
- **Touch-Friendly**: Large touch targets and swipe gestures
- **Offline Support**: Local data caching and sync
- **Pull-to-Refresh**: Intuitive data updates
- **Camera Integration**: Photo capture for items

## 🛠️ Technology Stack

### **Core Framework**
- **Flutter**: Latest stable version for cross-platform development
- **Dart**: Modern, fast programming language

### **State Management**
- **Riverpod**: Reactive state management with dependency injection
- **StateNotifier**: Immutable state management pattern

### **UI & Design**
- **Material Design 3**: Latest Material Design guidelines
- **Google Fonts**: Inter font family for modern typography
- **Flutter ScreenUtil**: Responsive design utilities
- **Custom Themes**: Light and dark theme support

### **Navigation**
- **GoRouter**: Declarative routing with deep linking
- **Route Guards**: Authentication-based route protection

### **Data & Storage**
- **Dio**: HTTP client for API communication
- **Hive**: Fast, lightweight local database
- **Flutter Secure Storage**: Encrypted storage for sensitive data
- **Shared Preferences**: Simple key-value storage

### **Forms & Validation**
- **Flutter Form Builder**: Advanced form handling
- **Form Validators**: Comprehensive input validation

### **Charts & Visualization**
- **FL Chart**: Beautiful, animated charts
- **Custom Widgets**: Tailored data visualization components

### **Development Tools**
- **JSON Annotation**: Automatic JSON serialization
- **Build Runner**: Code generation utilities
- **Flutter Lints**: Code quality and style enforcement

## 📦 Installation & Setup

### **Prerequisites**
- Flutter SDK (3.16.0 or later)
- Dart SDK (3.2.0 or later)
- IDE: VS Code or Android Studio
- Device/Emulator for testing

### **1. Clone the Repository**
```bash
git clone <repository-url>
cd import-logistics-frontend
```

### **2. Install Dependencies**
```bash
flutter pub get
```

### **3. Generate Code**
```bash
flutter packages pub run build_runner build
```

### **4. Configure API Endpoints**
Update `lib/core/constants/api_constants.dart`:
```dart
static const String baseUrl = 'http://your-backend-url:8000/api/v1';
```

### **5. Run the App**
```bash
# Development
flutter run

# Release build
flutter build apk  # Android
flutter build ios  # iOS
flutter build web  # Web
```

## 🔧 Configuration

### **Environment Setup**
Create environment-specific configurations:

```dart
// lib/core/constants/app_constants.dart
class AppConstants {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
}
```

### **Build Flavors**
```bash
# Development
flutter run --flavor dev --dart-define=API_BASE_URL=http://localhost:8000/api/v1

# Production  
flutter run --flavor prod --dart-define=API_BASE_URL=https://api.yourdomain.com/api/v1
```

### **Theme Customization**
Modify themes in `lib/presentation/themes/`:
- `light_theme.dart` - Light theme colors and styling
- `dark_theme.dart` - Dark theme colors and styling
- `app_theme.dart` - Common theme configuration

## 🎯 Usage Guide

### **Default Login**
```
Email: admin@example.com
Username: admin
Password: changethis
```

### **User Roles**
- **Admin**: Full system access, user management
- **Manager**: All containers, reports, team oversight  
- **Clerk**: Own containers only, basic operations
- **Viewer**: Read-only access to assigned data

### **Main Workflow**
1. **Login** with your credentials
2. **Create Container** (20ft or 40ft)
3. **Add Items** with purchase details and weights
4. **Add Expenses** (loading, shipping, clearing, etc.)
5. **Allocate Costs** to items (weight or value-based)
6. **Generate Pricing** recommendations
7. **Track Shipments** with MSC integration
8. **Analyze Reports** for profit optimization

### **Navigation**
- **Bottom Bar**: Primary navigation (Dashboard, Containers, Items, Reports, Settings)
- **FAB**: Quick access to create new containers
- **Drawer**: Additional features and user management
- **Search**: Global search across containers and items

## 🧪 Testing

### **Run Tests**
```bash
# Unit tests
flutter test

# Integration tests
flutter test integration_test/

# Widget tests
flutter test test/widget_test.dart
```

### **Test Coverage**
```bash
# Generate coverage report
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
open coverage/html/index.html
```

## 📱 Platform-Specific Features

### **Mobile Features**
- **Camera Integration**: Photo capture for items
- **Offline Mode**: Work without internet, sync later
- **Push Notifications**: Container status updates
- **Biometric Auth**: Fingerprint/Face ID login
- **Pull-to-Refresh**: Swipe down to update data

### **Desktop Features**  
- **Multiple Windows**: Side-by-side container management
- **Keyboard Shortcuts**: Power user productivity
- **File Import**: CSV/Excel bulk import
- **Advanced Filtering**: Complex search and filter options

### **Web Features**
- **Progressive Web App**: Install as web app
- **Responsive Layouts**: Desktop-class experience
- **Deep Linking**: Shareable URLs for items/containers
- **Print Support**: Generate reports and invoices

## 🎨 Customization

### **Branding**
Update app branding in:
- `lib/core/constants/app_constants.dart` - App name and version
- `android/app/src/main/res/` - Android app icon and splash
- `ios/Runner/Assets.xcassets/` - iOS app icon and splash
- `web/icons/` - Web app icons

### **Colors & Themes**
Customize the color scheme:
```dart
// lib/presentation/themes/app_theme.dart
static const Color primaryBlue = Color(0xFF2563EB); // Your brand color
static const Color successGreen = Color(0xFF059669); // Success color
static const Color warningOrange = Color(0xFFD97706); // Warning color
```

### **Localization**
Add multi-language support:
1. Add `flutter_localizations` dependency
2. Create `lib/l10n/` directory with translation files
3. Configure supported locales in `app.dart`

## 🚀 Deployment

### **Android**
```bash
# Build APK
flutter build apk --release

# Build App Bundle (recommended)
flutter build appbundle --release
```

### **iOS**
```bash
# Build iOS app
flutter build ios --release

# Create archive in Xcode
open ios/Runner.xcworkspace
```

### **Web**
```bash
# Build web app
flutter build web --release

# Deploy to hosting service
firebase deploy  # Firebase Hosting
netlify deploy   # Netlify
```

### **Desktop**
```bash
# Windows
flutter build windows --release

# macOS  
flutter build macos --release

# Linux
flutter build linux --release
```

## 📈 Performance Optimization

### **Best Practices**
- **Image Optimization**: Compress images and use appropriate formats
- **Lazy Loading**: Load data on-demand to reduce initial load time
- **Caching**: Implement smart caching strategies for offline support
- **State Management**: Use Riverpod for efficient state updates
- **Bundle Size**: Analyze and optimize app bundle size

### **Memory Management**
- **Dispose Controllers**: Always dispose text controllers and listeners
- **Image Caching**: Use `cached_network_image` for efficient image loading
- **List Performance**: Use `ListView.builder` for large lists

## 🔍 Troubleshooting

### **Common Issues**

**Build Errors:**
```bash
# Clean build
flutter clean
flutter pub get
flutter packages pub run build_runner build --delete-conflicting-outputs
```

**API Connection:**
- Check `api_constants.dart` for correct backend URL
- Verify backend is running and accessible
- Check network permissions in `android/app/src/main/AndroidManifest.xml`

**State Issues:**
- Restart app to reset state
- Check provider dependencies in `injection_container.dart`
- Verify API response format matches models

### **Debugging**
```bash
# Debug mode with logging
flutter run --debug

# Profile mode for performance
flutter run --profile

# Enable additional logging
flutter run --verbose
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### **Code Style**
- Follow [Effective Dart](https://dart.dev/guides/language/effective-dart) guidelines
- Use `flutter analyze` to check code quality
- Format code with `flutter format .`
- Add documentation for public APIs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flutter Team** for the amazing framework
- **Material Design** for design guidelines  
- **Riverpod** for excellent state management
- **Community** for open source packages

## 📞 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Create GitHub issues for bugs
- **Features**: Submit feature requests via GitHub
- **Email**: support@yourcompany.com

---

**Built with ❤️ using Flutter**

*This Flutter app perfectly complements the FastAPI backend to provide a complete Import Profit & Logistics Intelligence System.*