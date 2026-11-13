import 'dart:async';

import 'package:dio/dio.dart';

import 'config.dart';
import 'token_store.dart';

/// HTTP client: adds the access token, and on a 401 refreshes it ONCE and retries.
/// Refresh tokens rotate (each is single use), so concurrent 401s must share one refresh call.
class ApiClient {
  ApiClient(this._tokens, {required this.onSessionExpired}) {
    dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiBase,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Accept': 'application/json'},
    ));
    _bare = Dio(BaseOptions(
      baseUrl: AppConfig.apiBase,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 30),
    ));
    dio.interceptors.add(InterceptorsWrapper(onRequest: _attachToken, onError: _maybeRefresh));
  }

  final TokenStore _tokens;
  final void Function() onSessionExpired;
  late final Dio dio;
  late final Dio _bare; // no interceptors: used for login and refresh themselves
  Future<bool>? _refreshing;

  Dio get bare => _bare;

  Future<void> _attachToken(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _tokens.readAccess();
    if (token != null) options.headers['Authorization'] = 'Bearer $token';
    handler.next(options);
  }

  Future<void> _maybeRefresh(DioException err, ErrorInterceptorHandler handler) async {
    final request = err.requestOptions;
    final alreadyRetried = request.extra['retried'] == true;
    if (err.response?.statusCode != 401 || alreadyRetried) {
      return handler.next(err);
    }
    final ok = await (_refreshing ??= _refresh().whenComplete(() => _refreshing = null));
    if (!ok) {
      onSessionExpired();
      return handler.next(err);
    }
    try {
      request.extra['retried'] = true;
      final token = await _tokens.readAccess();
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      final response = await dio.fetch<dynamic>(request);
      handler.resolve(response);
    } on DioException catch (e) {
      handler.next(e);
    }
  }

  Future<bool> _refresh() async {
    final refresh = await _tokens.readRefresh();
    if (refresh == null) return false;
    try {
      final r = await _bare.post<Map<String, dynamic>>('/auth/refresh', data: {'refresh_token': refresh});
      final data = r.data;
      final access = data?['access_token'] as String?;
      if (access == null) return false;
      await _tokens.save(access: access, refresh: data?['refresh_token'] as String?);
      return true;
    } on DioException {
      return false;
    }
  }
}
