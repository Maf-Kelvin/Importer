#!/usr/bin/env bash
# Run ONCE after `flutter create .` (safe to run again). Makes the generated Android/iOS projects ready for this app:
#   * Android: INTERNET permission in the main manifest. Flutter only adds it for debug builds, so without this a
#     release build (the one you publish) cannot reach the server at all.
#   * Android debug builds: allow plain http, so the app can talk to your Mac during development.
#   * App name shown under the icon: "Importer" on both platforms.
set -euo pipefail
cd "$(dirname "$0")/.."

MAIN=android/app/src/main/AndroidManifest.xml
DEBUG=android/app/src/debug/AndroidManifest.xml
PLIST=ios/Runner/Info.plist

if [ ! -f "$MAIN" ]; then
  echo "android/ folder not found. Run: flutter create . --project-name importer_mobile --org com.importer --platforms=ios,android" >&2
  exit 1
fi

grep -q 'android.permission.INTERNET' "$MAIN" || perl -0pi -e 's#(<manifest[^>]*>)#$1\n    <uses-permission android:name="android.permission.INTERNET"/>#' "$MAIN"
perl -pi -e 's/android:label="importer_mobile"/android:label="Importer"/' "$MAIN"

if [ -f "$DEBUG" ]; then
  grep -q 'usesCleartextTraffic' "$DEBUG" || perl -0pi -e 's#</manifest>#    <application android:usesCleartextTraffic="true"/>\n</manifest>#' "$DEBUG"
fi

if [ -f "$PLIST" ] && [ -x /usr/libexec/PlistBuddy ]; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName Importer" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string Importer" "$PLIST"
fi

# iOS asks the person for permission the first time; the text below is what the dialog says.
# (Without these three entries the app CRASHES the moment the camera, microphone or photo library is opened.)
if [ -f "$PLIST" ] && [ -x /usr/libexec/PlistBuddy ]; then
  setkey() {
    /usr/libexec/PlistBuddy -c "Set :$1 $2" "$PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c "Add :$1 string $2" "$PLIST"
  }
  setkey NSCameraUsageDescription "Take photos and videos of your items."
  setkey NSMicrophoneUsageDescription "Record sound when you film an item."
  setkey NSPhotoLibraryUsageDescription "Choose photos and videos of your items."
fi

echo "Done. Check: grep -n INTERNET $MAIN ; grep -n Cleartext $DEBUG"
