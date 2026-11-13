import 'dart:math';

import 'package:dio/dio.dart';

/// One key per form submission. Reuse it when the same submission is retried, so a request
/// that reached the server but whose answer was lost cannot create a duplicate.
String newIdempotencyKey() {
  final rnd = Random.secure();
  final bytes = List<int>.generate(16, (_) => rnd.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

/// Dio options carrying the Idempotency-Key header.
Options idempotencyOptions(String key) => Options(headers: {'Idempotency-Key': key});
