import 'package:flutter_test/flutter_test.dart';
import 'package:importer_mobile/features/media/media_model.dart';

void main() {
  test('limits match the server (10 MB photo, 50 MB video, 6 photos, 1 video)', () {
    expect(MediaLimits.maxPhotoBytes, 10 * 1024 * 1024);
    expect(MediaLimits.maxVideoBytes, 50 * 1024 * 1024);
    expect(MediaLimits.maxPhotos, 6);
    expect(MediaLimits.maxVideos, 1);
  });

  test('megabytes formats sizes', () {
    expect(megabytes(1536 * 1024), '1.5 MB');
    expect(megabytes(50 * 1024 * 1024), '50 MB');
  });

  test('MediaItem reads the API and compares by id', () {
    final a = MediaItem.fromJson({'id': 3, 'item_id': 9, 'kind': 'video', 'file_size': 1000, 'file_url': '/api/v1/files/1/2/x.mp4'});
    expect(a.isVideo, isTrue);
    expect(a.itemId, 9);
    expect(a, MediaItem.fromJson({'id': 3, 'item_id': 9, 'kind': 'video', 'file_size': 5, 'file_url': '/x'}));
  });
}
