import 'package:dio/dio.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/errors.dart';
import '../containers/models.dart';
import 'media_model.dart';
import 'media_repository.dart';
import 'media_viewer.dart';

/// Photos and the short video of one item: add from the camera or the gallery, open, delete.
class ItemMediaScreen extends ConsumerStatefulWidget {
  const ItemMediaScreen({super.key, required this.item});
  final ItemModel item;

  @override
  ConsumerState<ItemMediaScreen> createState() => _ItemMediaScreenState();
}

enum _Pick { takePhoto, galleryPhoto, recordVideo, galleryVideo }

class _ItemMediaScreenState extends ConsumerState<ItemMediaScreen> {
  final _picker = ImagePicker();
  double? _progress; // null = not uploading
  CancelToken? _cancel;

  void _say(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _add(List<MediaItem> have) async {
    final photos = have.where((m) => !m.isVideo).length;
    final videos = have.where((m) => m.isVideo).length;
    final choice = await showModalBottomSheet<_Pick>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            enabled: photos < MediaLimits.maxPhotos,
            leading: const Icon(Icons.photo_camera_outlined),
            title: const Text('Take a photo'),
            onTap: () => Navigator.of(ctx).pop(_Pick.takePhoto),
          ),
          ListTile(
            enabled: photos < MediaLimits.maxPhotos,
            leading: const Icon(Icons.photo_library_outlined),
            title: const Text('Choose a photo'),
            subtitle: photos >= MediaLimits.maxPhotos ? const Text('Photo limit reached') : null,
            onTap: () => Navigator.of(ctx).pop(_Pick.galleryPhoto),
          ),
          ListTile(
            enabled: videos < MediaLimits.maxVideos,
            leading: const Icon(Icons.videocam_outlined),
            title: Text('Record a video (up to ${MediaLimits.maxVideoSeconds} seconds)'),
            onTap: () => Navigator.of(ctx).pop(_Pick.recordVideo),
          ),
          ListTile(
            enabled: videos < MediaLimits.maxVideos,
            leading: const Icon(Icons.video_library_outlined),
            title: Text('Choose a video (up to ${megabytes(MediaLimits.maxVideoBytes)})'),
            subtitle: videos >= MediaLimits.maxVideos ? const Text('Video limit reached') : null,
            onTap: () => Navigator.of(ctx).pop(_Pick.galleryVideo),
          ),
        ]),
      ),
    );
    if (choice == null || !mounted) return;

    XFile? file;
    final isVideo = choice == _Pick.recordVideo || choice == _Pick.galleryVideo;
    try {
      file = switch (choice) {
        _Pick.takePhoto => await _picker.pickImage(
            source: ImageSource.camera, maxWidth: MediaLimits.photoMaxSide, maxHeight: MediaLimits.photoMaxSide, imageQuality: MediaLimits.photoQuality),
        _Pick.galleryPhoto => await _picker.pickImage(
            source: ImageSource.gallery, maxWidth: MediaLimits.photoMaxSide, maxHeight: MediaLimits.photoMaxSide, imageQuality: MediaLimits.photoQuality),
        _Pick.recordVideo => await _picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: MediaLimits.maxVideoSeconds)),
        _Pick.galleryVideo => await _picker.pickVideo(source: ImageSource.gallery),
      };
    } on PlatformException {
      if (mounted) _say('Could not open the ${choice == _Pick.takePhoto || choice == _Pick.recordVideo ? 'camera' : 'gallery'}. Check that the app is allowed to use it in your phone settings.');
      return;
    }
    if (file == null || !mounted) return; // cancelled

    final cancel = CancelToken();
    setState(() {
      _progress = 0;
      _cancel = cancel;
    });
    try {
      await ref.read(mediaRepositoryProvider).upload(
            widget.item.id,
            file,
            isVideo: isVideo,
            cancel: cancel,
            onProgress: (p) {
              if (mounted) setState(() => _progress = p);
            },
          );
      if (mounted) _say(isVideo ? 'Video added.' : 'Photo added.');
    } on MediaTooLarge catch (e) {
      if (mounted) _say(e.message);
    } on DioException catch (e) {
      if (!mounted || CancelToken.isCancel(e)) {
        // cancelled by the person: say nothing
      } else if (e.response?.statusCode == 409) {
        _say('That file is already on this item.');
      } else if (e.response?.statusCode == 413) {
        _say('The file is too large for the server.');
      } else {
        _say(friendlyError(e));
      }
    } catch (e) {
      if (mounted) _say(friendlyError(e));
    } finally {
      if (mounted) {
        setState(() {
          _progress = null;
          _cancel = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = ref.watch(itemMediaProvider(widget.item.id));
    final uploading = _progress != null;
    return Scaffold(
      appBar: AppBar(title: Text(widget.item.name, overflow: TextOverflow.ellipsis)),
      floatingActionButton: media.hasValue && !uploading
          ? FloatingActionButton.extended(
              onPressed: () => _add(media.requireValue),
              icon: const Icon(Icons.add_a_photo_outlined),
              label: const Text('Add'),
            )
          : null,
      body: Column(
        children: [
          if (uploading)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('Uploading… ${(_progress! * 100).round()}%')),
                  TextButton(onPressed: () => _cancel?.cancel(), child: const Text('Cancel')),
                ]),
                LinearProgressIndicator(value: _progress == 0 ? null : _progress),
              ]),
            ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () => ref.refresh(itemMediaProvider(widget.item.id).future),
              child: media.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(32),
                  children: [
                    const SizedBox(height: 60),
                    Text(friendlyError(e), textAlign: TextAlign.center),
                    const SizedBox(height: 16),
                    Center(child: OutlinedButton(onPressed: () => ref.invalidate(itemMediaProvider(widget.item.id)), child: const Text('Try again'))),
                  ],
                ),
                data: (list) {
                  if (list.isEmpty) {
                    return ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(32),
                      children: const [
                        SizedBox(height: 60),
                        Icon(Icons.photo_outlined, size: 48),
                        SizedBox(height: 12),
                        Text('No photos or video yet.\nTap Add to take or choose one.', textAlign: TextAlign.center),
                      ],
                    );
                  }
                  return GridView.builder(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 3, crossAxisSpacing: 8, mainAxisSpacing: 8),
                    itemCount: list.length,
                    itemBuilder: (context, i) => _Tile(
                      media: list[i],
                      onTap: () async {
                        await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => MediaViewerScreen(media: list[i])));
                      },
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Tile extends ConsumerWidget {
  const _Tile({required this.media, required this.onTap});
  final MediaItem media;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    Widget child;
    if (media.isVideo) {
      child = Container(
        color: scheme.surfaceContainerHighest,
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          const Icon(Icons.play_circle_outline, size: 40),
          const SizedBox(height: 4),
          Text('Video · ${megabytes(media.size)}', style: Theme.of(context).textTheme.bodySmall),
        ]),
      );
    } else {
      child = ref.watch(mediaBytesProvider(media)).when(
            loading: () => Container(color: scheme.surfaceContainerHighest, child: const Center(child: CircularProgressIndicator(strokeWidth: 2))),
            error: (_, __) => Container(color: scheme.surfaceContainerHighest, child: const Icon(Icons.broken_image_outlined)),
            data: (bytes) => Image.memory(bytes, fit: BoxFit.cover, gaplessPlayback: true),
          );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: InkWell(onTap: onTap, child: child),
    );
  }
}
