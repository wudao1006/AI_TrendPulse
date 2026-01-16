import 'package:flutter/foundation.dart';

/// API配置
class ApiConfig {
  /// API基础URL（默认本机）
  static const String _defaultBaseUrl = 'http://localhost:8000/api/v1';

  /// Android 模拟器访问宿主机
  static const String _androidEmulatorBaseUrl = 'http://10.0.2.2:8000/api/v1';

  /// 允许通过 --dart-define 覆盖
  static const String _envBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const String _envApiKey = String.fromEnvironment('API_KEY');

  /// API基础URL
  static String get baseUrl {
    if (_envBaseUrl.isNotEmpty) {
      return _envBaseUrl;
    }
    if (kIsWeb) {
      return _defaultBaseUrl;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return _androidEmulatorBaseUrl;
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
      case TargetPlatform.fuchsia:
        return _defaultBaseUrl;
    }
  }

  /// API Key
  static String get apiKey => _envApiKey;

  /// 请求超时时间（秒）
  static const int connectTimeout = 30;
  static const int receiveTimeout = 60;

  /// 轮询间隔（毫秒）
  static const int pollingInterval = 2000;
}
