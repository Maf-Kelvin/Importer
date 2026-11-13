# Importer mobile (Flutter)

iOS and Android app for the Importer backend.

## First run
```
cd mobile
flutter create . --project-name importer_mobile --org com.importer --platforms=ios,android
flutter pub get
flutter analyze
flutter test
flutter run                                  # iOS Simulator: uses http://localhost:8000
flutter run --dart-define=API_BASE=http://10.0.2.2:8000/api/v1       # Android emulator
flutter run --dart-define=API_BASE=http://<Mac-LAN-IP>:8000/api/v1   # real phone, same Wi-Fi
```
`flutter create .` only adds the missing `ios/` and `android/` folders; it keeps these files.

Android blocks plain http by default. For development add `android:usesCleartextTraffic="true"`
to the `<application>` tag in `android/app/src/debug/AndroidManifest.xml`. Production uses https only.
