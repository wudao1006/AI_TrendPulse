import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/task.dart';
import '../models/analysis_result.dart';
import '../models/raw_data.dart';
import '../services/api_service.dart';

// API Service Provider
final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

// Task State
class TaskState {
  final Task? currentTask;
  final AnalysisResult? analysisResult;
  final List<RawData> rawDataList;
  final bool isLoading;
  final String? error;
  final bool isPolling;

  const TaskState({
    this.currentTask,
    this.analysisResult,
    this.rawDataList = const [],
    this.isLoading = false,
    this.error,
    this.isPolling = false,
  });

  TaskState copyWith({
    Task? currentTask,
    AnalysisResult? analysisResult,
    List<RawData>? rawDataList,
    bool? isLoading,
    String? error,
    bool? isPolling,
  }) {
    return TaskState(
      currentTask: currentTask ?? this.currentTask,
      analysisResult: analysisResult ?? this.analysisResult,
      rawDataList: rawDataList ?? this.rawDataList,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      isPolling: isPolling ?? this.isPolling,
    );
  }
}

// Task Notifier
class TaskNotifier extends StateNotifier<TaskState> {
  final ApiService _apiService;
  Timer? _pollingTimer;

  TaskNotifier(this._apiService) : super(const TaskState());

  // 创建新任务
  Future<void> createTask({
    required String keyword,
    required List<String> platforms,
    String language = 'en',
    String reportLanguage = 'auto',
    bool semanticSampling = false,
    int limitCount = 50,
    Map<String, dynamic>? platformConfigs,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final request = TaskCreate(
        keyword: keyword,
        platforms: platforms,
        language: language,
        reportLanguage: reportLanguage,
        semanticSampling: semanticSampling,
        limit: limitCount,
        platformConfigs: platformConfigs,
      );
      final response = await _apiService.createTask(request);
      final task = Task.fromCreateResponse(
        response,
        keyword: keyword,
        platforms: platforms,
        limitCount: limitCount,
      );
      state = state.copyWith(
        currentTask: task,
        isLoading: false,
        analysisResult: null,
        rawDataList: [],
      );
      // 开始轮询任务状态
      _startPolling(task.id);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 开始轮询
  void _startPolling(String taskId) {
    _stopPolling();
    state = state.copyWith(isPolling: true);

    _pollingTimer = Timer.periodic(
      const Duration(seconds: 2),
      (_) => _pollTaskStatus(taskId),
    );
  }

  // 停止轮询
  void _stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    state = state.copyWith(isPolling: false);
  }

  // 轮询任务状态
  Future<void> _pollTaskStatus(String taskId) async {
    try {
      final response = await _apiService.getTaskStatus(taskId);
      final limitCount = state.currentTask?.limitCount ?? 0;
      final task = Task.fromStatusResponse(response, limitCount: limitCount);
      state = state.copyWith(currentTask: task);

      if (task.status == TaskStatus.completed) {
        _stopPolling();
        await _loadResults(taskId);
      } else if (task.status == TaskStatus.failed) {
        _stopPolling();
        state = state.copyWith(error: task.errorMessage ?? '任务失败');
      }
    } catch (e) {
      // 轮询出错时不停止，继续尝试
      print('轮询出错: $e');
    }
  }

  // 加载分析结果
  Future<void> _loadResults(String taskId) async {
    try {
      final result = await _apiService.getTaskResult(taskId);
      final rawData = await _apiService.getRawData(taskId);
      state = state.copyWith(
        analysisResult: result,
        rawDataList: rawData.data,
      );
    } catch (e) {
      state = state.copyWith(error: '加载结果失败: $e');
    }
  }

  // 手动刷新
  Future<void> refresh() async {
    final task = state.currentTask;
    if (task != null) {
      await _pollTaskStatus(task.id);
    }
  }

  // 加载已有任务
  Future<void> loadTask(
    String taskId, {
    int? limitCount,
  }) async {
    _stopPolling();
    state = state.copyWith(isLoading: true, error: null, analysisResult: null, rawDataList: []);

    try {
      final response = await _apiService.getTaskStatus(taskId);
      final task = Task.fromStatusResponse(
        response,
        limitCount: limitCount ?? 0,
      );
      state = state.copyWith(currentTask: task, isLoading: false);

      if (task.status == TaskStatus.completed) {
        await _loadResults(task.id);
      } else if (task.status == TaskStatus.failed) {
        state = state.copyWith(error: task.errorMessage ?? '任务失败');
      } else {
        _startPolling(task.id);
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  // 清除当前任务
  void clearTask() {
    _stopPolling();
    state = const TaskState();
  }

  @override
  void dispose() {
    _stopPolling();
    super.dispose();
  }
}

// Provider
final taskProvider = StateNotifierProvider<TaskNotifier, TaskState>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  return TaskNotifier(apiService);
});

// 平台列表Provider
final platformsProvider = FutureProvider<List<String>>((ref) async {
  final apiService = ref.watch(apiServiceProvider);
  return apiService.getPlatforms();
});

class RawDataParams {
  final String taskId;
  final String? platform;
  final int page;
  final int pageSize;

  const RawDataParams({
    required this.taskId,
    this.platform,
    this.page = 1,
    this.pageSize = 20,
  });

  @override
  bool operator ==(Object other) {
    return other is RawDataParams &&
        other.taskId == taskId &&
        other.platform == platform &&
        other.page == page &&
        other.pageSize == pageSize;
  }

  @override
  int get hashCode {
    return Object.hash(taskId, platform, page, pageSize);
  }
}

final rawDataProvider =
    FutureProvider.family<RawDataListResponse, RawDataParams>((ref, params) async {
  final apiService = ref.watch(apiServiceProvider);
  return apiService.getRawData(
    params.taskId,
    page: params.page,
    pageSize: params.pageSize,
    platform: params.platform,
  );
});
