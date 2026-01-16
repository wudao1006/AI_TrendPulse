/// 任务状态枚举
enum TaskStatus {
  pending,
  running,
  completed,
  failed;

  static TaskStatus fromString(String value) {
    return TaskStatus.values.firstWhere(
      (e) => e.name == value,
      orElse: () => TaskStatus.pending,
    );
  }
}

/// 任务实体
class Task {
  final String id;
  final String keyword;
  final List<String> platforms;
  final TaskStatus status;
  final int progress;
  final int limitCount;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;

  Task({
    required this.id,
    required this.keyword,
    required this.platforms,
    required this.status,
    required this.progress,
    required this.limitCount,
    this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  Task copyWith({
    String? id,
    String? keyword,
    List<String>? platforms,
    TaskStatus? status,
    int? progress,
    int? limitCount,
    String? errorMessage,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Task(
      id: id ?? this.id,
      keyword: keyword ?? this.keyword,
      platforms: platforms ?? this.platforms,
      status: status ?? this.status,
      progress: progress ?? this.progress,
      limitCount: limitCount ?? this.limitCount,
      errorMessage: errorMessage ?? this.errorMessage,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  factory Task.fromCreateResponse(
    TaskResponse response, {
    required String keyword,
    required List<String> platforms,
    required int limitCount,
  }) {
    return Task(
      id: response.taskId,
      keyword: keyword,
      platforms: platforms,
      status: TaskStatus.fromString(response.status),
      progress: 0,
      limitCount: limitCount,
      createdAt: response.createdAt,
      updatedAt: response.createdAt,
    );
  }

  factory Task.fromStatusResponse(
    TaskStatusResponse response, {
    required int limitCount,
  }) {
    return Task(
      id: response.taskId,
      keyword: response.keyword,
      platforms: response.platforms,
      status: response.status,
      progress: response.progress,
      limitCount: limitCount,
      errorMessage: response.errorMessage,
      createdAt: response.createdAt,
      updatedAt: response.updatedAt,
    );
  }
}

/// 创建任务请求
class TaskCreate {
  final String keyword;
  final String language;
  final String reportLanguage;
  final bool semanticSampling;
  final int limit;
  final List<String> platforms;
  final Map<String, dynamic>? platformConfigs;

  TaskCreate({
    required this.keyword,
    this.language = 'en',
    this.reportLanguage = 'auto',
    this.semanticSampling = false,
    this.limit = 50,
    required this.platforms,
    this.platformConfigs,
  });

  Map<String, dynamic> toJson() => {
    'keyword': keyword,
    'language': language,
    'report_language': reportLanguage,
    'semantic_sampling': semanticSampling,
    'limit': limit,
    'platforms': platforms,
    'platform_configs': platformConfigs,
  };
}

/// 任务响应
class TaskResponse {
  final String taskId;
  final String status;
  final DateTime createdAt;

  TaskResponse({
    required this.taskId,
    required this.status,
    required this.createdAt,
  });

  factory TaskResponse.fromJson(Map<String, dynamic> json) {
    return TaskResponse(
      taskId: json['task_id'],
      status: json['status'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

/// 任务状态响应
class TaskStatusResponse {
  final String taskId;
  final String keyword;
  final List<String> platforms;
  final TaskStatus status;
  final int progress;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;

  TaskStatusResponse({
    required this.taskId,
    required this.keyword,
    required this.platforms,
    required this.status,
    required this.progress,
    this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TaskStatusResponse.fromJson(Map<String, dynamic> json) {
    return TaskStatusResponse(
      taskId: json['task_id'],
      keyword: json['keyword'],
      platforms: List<String>.from(json['platforms']),
      status: TaskStatus.fromString(json['status']),
      progress: json['progress'],
      errorMessage: json['error_message'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

/// 任务列表项
class TaskSummary {
  final String taskId;
  final String keyword;
  final List<String> platforms;
  final TaskStatus status;
  final int progress;
  final int limitCount;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;

  TaskSummary({
    required this.taskId,
    required this.keyword,
    required this.platforms,
    required this.status,
    required this.progress,
    required this.limitCount,
    this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TaskSummary.fromJson(Map<String, dynamic> json) {
    return TaskSummary(
      taskId: json['task_id'],
      keyword: json['keyword'],
      platforms: List<String>.from(json['platforms']),
      status: TaskStatus.fromString(json['status']),
      progress: json['progress'],
      limitCount: json['limit_count'],
      errorMessage: json['error_message'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
}

/// 任务列表响应
class TaskListResponse {
  final int total;
  final int page;
  final int pageSize;
  final List<TaskSummary> data;

  TaskListResponse({
    required this.total,
    required this.page,
    required this.pageSize,
    required this.data,
  });

  factory TaskListResponse.fromJson(Map<String, dynamic> json) {
    return TaskListResponse(
      total: json['total'],
      page: json['page'],
      pageSize: json['page_size'],
      data: (json['data'] as List)
          .map((item) => TaskSummary.fromJson(item))
          .toList(),
    );
  }
}
