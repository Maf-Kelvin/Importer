/// Limits applied on the phone BEFORE uploading (the server enforces the same ones).
class MediaLimits {
  static const maxPhotoBytes = 10 * 1024 * 1024; // 10 MB
  static const maxVideoBytes = 50 * 1024 * 1024; // 50 MB
  static const maxVideoSeconds = 30;
  static const maxPhotos = 6;
  static const maxVideos = 1;

  /// Photos are shrunk to this size and quality as they are picked: a phone photo drops from ~5 MB to ~300 KB.
  static const photoMaxSide = 1600.0;
  static const photoQuality = 80;
}

class MediaItem {
  const MediaItem({required this.id, required this.itemId, required this.kind, required this.size, required this.url});
  final int id;
  final int itemId;
  final String kind; // photo | video
  final int size;
  final String url; // path on the API server, e.g. /api/v1/files/1/2/abc.jpg

  bool get isVideo => kind == 'video';

  factory MediaItem.fromJson(Map<String, dynamic> j) => MediaItem(
        id: j['id'] as int,
        itemId: j['item_id'] as int,
        kind: (j['kind'] as String?) ?? 'photo',
        size: (j['file_size'] as num?)?.toInt() ?? 0,
        url: j['file_url'] as String,
      );

  @override
  bool operator ==(Object other) => other is MediaItem && other.id == id;

  @override
  int get hashCode => id.hashCode;
}

String megabytes(int bytes) => '${(bytes / (1024 * 1024)).toStringAsFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB';
