import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/task.dart';
import '../models/raw_data.dart';
import '../models/analysis_result.dart';
import '../models/subscription.dart';

/// API服务
class ApiService {
  static final ApiService _instance = ApiService._internal();
  factory ApiService() => _instance;

  late final Dio _dio;

  ApiService._internal() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.baseUrl,
      connectTimeout: Duration(seconds: ApiConfig.connectTimeout),
      receiveTimeout: Duration(seconds: ApiConfig.receiveTimeout),
      headers: {
        'Content-Type': 'application/json',
        if (ApiConfig.apiKey.isNotEmpty)
          'Authorization': 'Bearer ${ApiConfig.apiKey}',
      },
    ));

    // 添加日志拦截器（调试用）
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
    ));
  }

  // ==================== 任务相关 ====================

  /// 创建任务
  Future<TaskResponse> createTask(TaskCreate task) async {
    final response = await _dio.post('/tasks', data: task.toJson());
    return TaskResponse.fromJson(response.data);
  }

  /// 获取任务状态
  Future<TaskStatusResponse> getTaskStatus(String taskId) async {
    final response = await _dio.get('/tasks/$taskId');
    return TaskStatusResponse.fromJson(response.data);
  }

  /// 获取任务历史列表
  Future<TaskListResponse> getTaskList({
    int page = 1,
    int pageSize = 20,
    String? status,
    String? keyword,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    if (keyword != null && keyword.isNotEmpty) {
      queryParams['keyword'] = keyword;
    }

    final response = await _dio.get('/tasks', queryParameters: queryParams);
    return TaskListResponse.fromJson(response.data);
  }

  /// 获取分析结果
  Future<AnalysisResult> getTaskResult(String taskId) async {
    final response = await _dio.get('/tasks/$taskId/result');
    return AnalysisResult.fromJson(response.data);
  }

  /// 删除任务
  Future<void> deleteTask(String taskId) async {
    await _dio.delete('/tasks/$taskId');
  }

  /// 获取原始数据
  Future<RawDataListResponse> getRawData(
    String taskId, {
    int page = 1,
    int pageSize = 20,
    String? platform,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
    };
    if (platform != null) {
      queryParams['platform'] = platform;
    }

    final response = await _dio.get(
      '/tasks/$taskId/raw-data',
      queryParameters: queryParams,
    );
    return RawDataListResponse.fromJson(response.data);
  }

  // ==================== 平台相关 ====================

  /// 获取支持的平台列表
  Future<List<String>> getPlatforms() async {
    final response = await _dio.get('/platforms');
    return List<String>.from(response.data);
  }

  // ==================== 订阅相关 ====================

  /// 创建订阅
  Future<Subscription> createSubscription(SubscriptionCreate subscription) async {
    final response = await _dio.post('/subscriptions', data: subscription.toJson());
    return Subscription.fromJson(response.data);
  }

  /// 获取订阅列表
  Future<List<Subscription>> getSubscriptions() async {
    final response = await _dio.get('/subscriptions');
    return (response.data as List)
        .map((item) => Subscription.fromJson(item))
        .toList();
  }

  /// 更新订阅
  Future<Subscription> updateSubscription(
    String subscriptionId,
    Map<String, dynamic> data,
  ) async {
    final response = await _dio.put('/subscriptions/$subscriptionId', data: data);
    return Subscription.fromJson(response.data);
  }

  /// 删除订阅
  Future<void> deleteSubscription(String subscriptionId) async {
    await _dio.delete('/subscriptions/$subscriptionId');
  }

  /// 获取订阅的调度任务信息
  Future<SubscriptionJobInfo> getSubscriptionJobInfo(String subscriptionId) async {
    final response = await _dio.get('/subscriptions/$subscriptionId/job');
    return SubscriptionJobInfo.fromJson(response.data);
  }

  /// 获取订阅趋势
  Future<SubscriptionTrendResponse> getSubscriptionTrend(
    String subscriptionId, {
    int limit = 10,
  }) async {
    final response = await _dio.get(
      '/subscriptions/$subscriptionId/trend',
      queryParameters: {'limit': limit},
    );
    return SubscriptionTrendResponse.fromJson(response.data);
  }

  /// 获取调度器状态
  Future<SchedulerStatus> getSchedulerStatus() async {
    final response = await _dio.get('/subscriptions/scheduler/status');
    return SchedulerStatus.fromJson(response.data);
  }

  /// 立即触发订阅任务（手动执行）
  Future<void> triggerSubscription(String subscriptionId) async {
    await _dio.post('/subscriptions/$subscriptionId/trigger');
  }

  // ==================== 报警相关 ====================

  /// 获取报警列表
  Future<List<Alert>> getAlerts({bool? isRead}) async {
    final queryParams = <String, dynamic>{};
    if (isRead != null) {
      queryParams['is_read'] = isRead;
    }

    final response = await _dio.get('/alerts', queryParameters: queryParams);
    return (response.data as List)
        .map((item) => Alert.fromJson(item))
        .toList();
  }

  /// 标记报警为已读
  Future<void> markAlertRead(String alertId) async {
    await _dio.put('/alerts/$alertId/read');
  }

  /// 标记所有报警为已读
  Future<void> markAllAlertsRead() async {
    await _dio.put('/alerts/read-all');
  }
}
