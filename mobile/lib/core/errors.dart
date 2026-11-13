import 'package:dio/dio.dart';

/// Turns any failure into one sentence a person can act on.
String friendlyError(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map && data['detail'] != null) {
      final detail = data['detail'];
      if (detail is String) return detail;
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && first['msg'] is String) return first['msg'] as String;
      }
    }
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'The server took too long to answer. Try again.';
      case DioExceptionType.connectionError:
        return 'Cannot reach the server. Check your connection and the API address.';
      default:
        break;
    }
    final code = error.response?.statusCode;
    if (code == 401) return 'Your session has ended. Please sign in again.';
    if (code == 403) return 'You do not have permission to do that.';
    if (code != null && code >= 500) return 'The server had a problem. Try again shortly.';
  }
  return 'Something went wrong. Try again.';
}
