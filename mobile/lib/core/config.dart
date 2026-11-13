/// Where the API lives. Override per run, for example:
///   flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api/v1     (Android emulator)
///   flutter run --dart-define=API_BASE=http://192.168.1.20:8000/api/v1 (real phone on your Wi-Fi)
/// The iOS Simulator can use the default, because it shares your Mac's localhost.
class AppConfig {
  static const String apiBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://localhost:8000/api/v1',
  );
}
