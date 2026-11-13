import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/config.dart';
import '../../core/providers.dart';
import 'media_model.dart';

/// Photos and videos of one item.
final itemMediaProvider = FutureProvider.autoDispose.family<List<MediaItem>, int>((ref, itemId) async {
  final r = await ref.read(apiClientProvider).dio.get<List<dynamic>>('/items/$itemId/media');
  return (r.data ?? const []).map((e) => MediaItem.fromJson(e as Map<String, dynamic>)).toList();
});

/// A photo's bytes (downloaded with the sign-in token; the file URLs are not public).
final mediaBytesProvider = FutureProvider.autoDispose.family<Uint8List, MediaItem>((ref, media) async {
  final r = await ref.read(apiClientProvider).dio.get<List<int>>(
        _relative(media.url),
        options: Options(responseType: ResponseType.bytes, receiveTimeout: const Duration(minutes: 2)),
      );
  return Uint8List.fromList(r.data ?? const []);
});

/// The API is mounted under [AppConfig.apiBase] (which already ends in /api/v1), so drop that prefix from file URLs.
String _relative(String url) {
  final prefix = Uri.parse(AppConfig.apiBase).path; // "/api/v1"
  return url.startsWith(prefix) ? url.substring(prefix.length) : url;
}

class MediaTooLarge implements Exception {
  MediaTooLarge(this.message);
  final String message;
}

class MediaRepository {
  MediaRepository(this._ref);
  final Ref _ref;

  Dio get _dio => _ref.read(apiClientProvider).dio;

  /// Checks the size, then uploads. [onProgress] gets 0.0 .. 1.0.
  /// No Idempotency-Key is sent on purpose (the server would hold the whole file in memory to fingerprint it);
  /// sending the same picture twice is answered with a 409 instead, so a retry is safe.
  Future<void> upload(int itemId, XFile file, {required bool isVideo, void Function(double)? onProgress, CancelToken? cancel}) async {
    final size = await file.length();
    final cap = isVideo ? MediaLimits.maxVideoBytes : MediaLimits.maxPhotoBytes;
    if (size > cap) {
      throw MediaTooLarge('That ${isVideo ? 'video' : 'photo'} is ${megabytes(size)}. The limit is ${megabytes(cap)}.');
    }
    // A cheap call first: if the sign-in token expired it is renewed now. A file upload cannot be replayed after a 401.
    await _dio.get<dynamic>('/items/$itemId/media');
    final form = FormData.fromMap({'file': await MultipartFile.fromFile(file.path, filename: file.name)});
    await _dio.post<dynamic>(
      '/items/$itemId/media',
      data: form,
      cancelToken: cancel,
      options: Options(sendTimeout: const Duration(minutes: 5), receiveTimeout: const Duration(minutes: 1)),
      onSendProgress: (sent, total) {
        if (total > 0) onProgress?.call(sent / total);
      },
    );
    _ref.invalidate(itemMediaProvider(itemId));
  }

  Future<void> delete(MediaItem m) async {
    await _dio.delete<dynamic>('/items/${m.itemId}/media/${m.id}');
    _ref.invalidate(itemMediaProvider(m.itemId));
  }

  /// Downloads a video to a temporary file so the player can open it (the server has no streaming/seek support).
  Future<File> downloadVideo(MediaItem m, {void Function(double)? onProgress}) async {
    final dir = await getTemporaryDirectory();
    final ext = m.url.contains('.') ? m.url.substring(m.url.lastIndexOf('.')) : '.mp4';
    final file = File('${dir.path}/item_${m.itemId}_media_${m.id}$ext');
    if (await file.exists() && await file.length() == m.size) return file;
    await _dio.download(
      _relative(m.url),
      file.path,
      options: Options(receiveTimeout: const Duration(minutes: 5)),
      onReceiveProgress: (got, total) {
        if (total > 0) onProgress?.call(got / total);
      },
    );
    return file;
  }
}

final mediaRepositoryProvider = Provider<MediaRepository>(MediaRepository.new);
