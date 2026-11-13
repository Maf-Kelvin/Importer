import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../../core/confirm.dart';
import '../../core/errors.dart';
import 'media_model.dart';
import 'media_repository.dart';

/// Full-screen photo (pinch to zoom) or video player, with a delete button.
class MediaViewerScreen extends ConsumerStatefulWidget {
  const MediaViewerScreen({super.key, required this.media});
  final MediaItem media;

  @override
  ConsumerState<MediaViewerScreen> createState() => _MediaViewerScreenState();
}

class _MediaViewerScreenState extends ConsumerState<MediaViewerScreen> {
  VideoPlayerController? _video;
  double _download = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.media.isVideo) _loadVideo();
  }

  Future<void> _loadVideo() async {
    try {
      final file = await ref.read(mediaRepositoryProvider).downloadVideo(widget.media, onProgress: (p) {
        if (mounted) setState(() => _download = p);
      });
      final controller = VideoPlayerController.file(file);
      await controller.initialize();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      controller.addListener(() {
        if (mounted) setState(() {});
      });
      setState(() => _video = controller);
      await controller.play();
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    }
  }

  @override
  void dispose() {
    _video?.dispose();
    super.dispose();
  }

  Future<void> _delete() async {
    final ok = await confirmDialog(context, title: 'Delete this ${widget.media.isVideo ? 'video' : 'photo'}?', message: 'It will be removed from the item.');
    if (!ok || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    final nav = Navigator.of(context);
    try {
      await ref.read(mediaRepositoryProvider).delete(widget.media);
      nav.pop();
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        actions: [IconButton(tooltip: 'Delete', icon: const Icon(Icons.delete_outline), onPressed: _delete)],
      ),
      body: Center(child: widget.media.isVideo ? _videoBody() : _photoBody()),
    );
  }

  Widget _photoBody() {
    return ref.watch(mediaBytesProvider(widget.media)).when(
          loading: () => const CircularProgressIndicator(),
          error: (e, _) => Text(friendlyError(e), style: const TextStyle(color: Colors.white)),
          data: (bytes) => InteractiveViewer(minScale: 1, maxScale: 5, child: Image.memory(bytes, fit: BoxFit.contain)),
        );
  }

  Widget _videoBody() {
    if (_error != null) return Text(_error!, style: const TextStyle(color: Colors.white), textAlign: TextAlign.center);
    final v = _video;
    if (v == null) {
      return Column(mainAxisSize: MainAxisSize.min, children: [
        SizedBox(width: 200, child: LinearProgressIndicator(value: _download == 0 ? null : _download)),
        const SizedBox(height: 12),
        const Text('Loading video…', style: TextStyle(color: Colors.white)),
      ]);
    }
    return Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      AspectRatio(aspectRatio: v.value.aspectRatio, child: VideoPlayer(v)),
      VideoProgressIndicator(v, allowScrubbing: true, padding: const EdgeInsets.all(12)),
      IconButton(
        iconSize: 48,
        color: Colors.white,
        icon: Icon(v.value.isPlaying ? Icons.pause_circle_outline : Icons.play_circle_outline),
        onPressed: () => v.value.isPlaying ? v.pause() : v.play(),
      ),
    ]);
  }
}
