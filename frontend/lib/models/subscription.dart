/// 订阅模型
class Subscription {
  final String id;
  final String keyword;
  final List<String> platforms;
  final String language;
  final String reportLanguage;
  final bool semanticSampling;
  final int limit;
  final int intervalHours;
  final int? intervalMinutes;
  final int alertThreshold;
  final bool isActive;
  final DateTime? lastRunAt;
  final DateTime? nextRunAt;
  final DateTime createdAt;
  final Map<String, dynamic>? platformConfigs;

  Subscription({
    required this.id,
    required this.keyword,
    required this.platforms,
    required this.language,
    required this.reportLanguage,
    required this.semanticSampling,
    required this.limit,
    required this.intervalHours,
    this.intervalMinutes,
    required this.alertThreshold,
    required this.isActive,
    this.lastRunAt,
    this.nextRunAt,
    required this.createdAt,
    this.platformConfigs,
  });

  factory Subscription.fromJson(Map<String, dynamic> json) {
    return Subscription(
      id: json['id'],
      keyword: json['keyword'],
      platforms: List<String>.from(json['platforms']),
      language: json['language'],
      reportLanguage: json['report_language'] ?? 'auto',
      semanticSampling: json['semantic_sampling'] ?? false,
      limit: json['limit'] ?? 50,
      intervalHours: json['interval_hours'],
      intervalMinutes: json['interval_minutes'],
      alertThreshold: json['alert_threshold'],
      isActive: json['is_active'],
      lastRunAt: json['last_run_at'] != null
          ? DateTime.parse(json['last_run_at'])
          : null,
      nextRunAt: json['next_run_at'] != null
          ? DateTime.parse(json['next_run_at'])
          : null,
      createdAt: DateTime.parse(json['created_at']),
      platformConfigs: json['platform_configs'] != null
          ? Map<String, dynamic>.from(json['platform_configs'])
          : null,
    );
  }
}

/// 创建订阅请求
class SubscriptionCreate {
  final String keyword;
  final List<String> platforms;
  final String language;
  final String reportLanguage;
  final bool semanticSampling;
  final int limit;
  final int intervalHours;
  final int? intervalMinutes;
  final int alertThreshold;
  final Map<String, dynamic>? platformConfigs;

  SubscriptionCreate({
    required this.keyword,
    required this.platforms,
    this.language = 'en',
    this.reportLanguage = 'auto',
    this.semanticSampling = false,
    this.limit = 50,
    this.intervalHours = 6,
    this.intervalMinutes,
    this.alertThreshold = 30,
    this.platformConfigs,
  });

  Map<String, dynamic> toJson() => {
    'keyword': keyword,
    'platforms': platforms,
    'language': language,
    'report_language': reportLanguage,
    'semantic_sampling': semanticSampling,
    'limit': limit,
    'interval_hours': intervalHours,
    'interval_minutes': intervalMinutes,
    'alert_threshold': alertThreshold,
    'platform_configs': platformConfigs,
  };
}

/// 报警模型
class Alert {
  final String id;
  final String subscriptionId;
  final String? taskId;
  final int sentimentScore;
  final String alertType;
  final bool isRead;
  final DateTime createdAt;

  Alert({
    required this.id,
    required this.subscriptionId,
    this.taskId,
    required this.sentimentScore,
    required this.alertType,
    required this.isRead,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      id: json['id'],
      subscriptionId: json['subscription_id'],
      taskId: json['task_id'],
      sentimentScore: json['sentiment_score'],
      alertType: json['alert_type'],
      isRead: json['is_read'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

/// 调度任务信息
class SchedulerJobInfo {
  final String jobId;
  final DateTime? nextRunTime;
  final String trigger;

  SchedulerJobInfo({
    required this.jobId,
    this.nextRunTime,
    required this.trigger,
  });

  factory SchedulerJobInfo.fromJson(Map<String, dynamic> json) {
    return SchedulerJobInfo(
      jobId: json['job_id'],
      nextRunTime: json['next_run_time'] != null
          ? DateTime.parse(json['next_run_time'])
          : null,
      trigger: json['trigger'] ?? '',
    );
  }
}

/// 调度器状态
class SchedulerStatus {
  final bool schedulerEnabled;
  final bool initialized;
  final bool lockAcquired;
  final int jobCount;

  SchedulerStatus({
    required this.schedulerEnabled,
    required this.initialized,
    required this.lockAcquired,
    required this.jobCount,
  });

  factory SchedulerStatus.fromJson(Map<String, dynamic> json) {
    return SchedulerStatus(
      schedulerEnabled: json['scheduler_enabled'] ?? false,
      initialized: json['initialized'] ?? false,
      lockAcquired: json['lock_acquired'] ?? false,
      jobCount: json['job_count'] ?? 0,
    );
  }
}

/// 订阅调度任务信息响应
class SubscriptionJobInfo {
  final String subscriptionId;
  final bool isActive;
  final int intervalHours;
  final int? intervalMinutes;
  final DateTime? lastRunAt;
  final DateTime? nextRunAt;
  final SchedulerJobInfo? job;
  final SchedulerStatus? scheduler;

  SubscriptionJobInfo({
    required this.subscriptionId,
    required this.isActive,
    required this.intervalHours,
    this.intervalMinutes,
    this.lastRunAt,
    this.nextRunAt,
    this.job,
    this.scheduler,
  });

  factory SubscriptionJobInfo.fromJson(Map<String, dynamic> json) {
    return SubscriptionJobInfo(
      subscriptionId: json['subscription_id'],
      isActive: json['is_active'],
      intervalHours: json['interval_hours'],
      intervalMinutes: json['interval_minutes'],
      lastRunAt: json['last_run_at'] != null
          ? DateTime.parse(json['last_run_at'])
          : null,
      nextRunAt: json['next_run_at'] != null
          ? DateTime.parse(json['next_run_at'])
          : null,
      job: json['job'] != null
          ? SchedulerJobInfo.fromJson(json['job'])
          : null,
      scheduler: json['scheduler'] != null
          ? SchedulerStatus.fromJson(json['scheduler'])
          : null,
    );
  }
}

class SubscriptionTrendPoint {
  final String taskId;
  final int sentimentScore;
  final double heatIndex;
  final DateTime analyzedAt;

  SubscriptionTrendPoint({
    required this.taskId,
    required this.sentimentScore,
    required this.heatIndex,
    required this.analyzedAt,
  });

  factory SubscriptionTrendPoint.fromJson(Map<String, dynamic> json) {
    return SubscriptionTrendPoint(
      taskId: json['task_id'],
      sentimentScore: json['sentiment_score'],
      heatIndex: (json['heat_index'] as num).toDouble(),
      analyzedAt: DateTime.parse(json['analyzed_at']),
    );
  }
}

class SubscriptionTrendResponse {
  final String subscriptionId;
  final List<SubscriptionTrendPoint> points;

  SubscriptionTrendResponse({
    required this.subscriptionId,
    required this.points,
  });

  factory SubscriptionTrendResponse.fromJson(Map<String, dynamic> json) {
    return SubscriptionTrendResponse(
      subscriptionId: json['subscription_id'],
      points: (json['points'] as List)
          .map((item) => SubscriptionTrendPoint.fromJson(item))
          .toList(),
    );
  }
}
