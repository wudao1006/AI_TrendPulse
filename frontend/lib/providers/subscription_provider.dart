import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/subscription.dart';
import '../services/api_service.dart';
import 'task_provider.dart';

// Subscription State
class SubscriptionState {
  final List<Subscription> subscriptions;
  final List<Alert> alerts;
  final int unreadCount;
  final SchedulerStatus? schedulerStatus;
  final bool isLoading;
  final String? error;

  const SubscriptionState({
    this.subscriptions = const [],
    this.alerts = const [],
    this.unreadCount = 0,
    this.schedulerStatus,
    this.isLoading = false,
    this.error,
  });

  SubscriptionState copyWith({
    List<Subscription>? subscriptions,
    List<Alert>? alerts,
    int? unreadCount,
    SchedulerStatus? schedulerStatus,
    bool? isLoading,
    String? error,
  }) {
    return SubscriptionState(
      subscriptions: subscriptions ?? this.subscriptions,
      alerts: alerts ?? this.alerts,
      unreadCount: unreadCount ?? this.unreadCount,
      schedulerStatus: schedulerStatus ?? this.schedulerStatus,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// Subscription Notifier
class SubscriptionNotifier extends StateNotifier<SubscriptionState> {
  final ApiService _apiService;

  SubscriptionNotifier(this._apiService) : super(const SubscriptionState());

  // 加载订阅列表
  Future<void> loadSubscriptions() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final subscriptions = await _apiService.getSubscriptions();
      state = state.copyWith(
        subscriptions: subscriptions,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 创建订阅
  Future<void> createSubscription(SubscriptionCreate subscription) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final created = await _apiService.createSubscription(subscription);
      state = state.copyWith(
        subscriptions: [...state.subscriptions, created],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // 更新订阅
  Future<void> updateSubscription(String id, Map<String, dynamic> data) async {
    try {
      final updated = await _apiService.updateSubscription(id, data);
      final index = state.subscriptions.indexWhere((s) => s.id == id);
      if (index == -1) return;
      final newList = [...state.subscriptions];
      newList[index] = updated;
      state = state.copyWith(subscriptions: newList);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> toggleSubscription(String id, bool isActive) async {
    await updateSubscription(id, {'is_active': isActive});
  }

  // 删除订阅
  Future<void> deleteSubscription(String id) async {
    try {
      await _apiService.deleteSubscription(id);
      state = state.copyWith(
        subscriptions: state.subscriptions.where((s) => s.id != id).toList(),
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  // 立即触发订阅任务
  Future<bool> triggerSubscription(String id) async {
    try {
      await _apiService.triggerSubscription(id);
      return true;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return false;
    }
  }

  // 获取订阅的调度任务信息
  Future<SubscriptionJobInfo?> getJobInfo(String id) async {
    try {
      return await _apiService.getSubscriptionJobInfo(id);
    } catch (e) {
      state = state.copyWith(error: e.toString());
      return null;
    }
  }

  Future<void> loadSchedulerStatus() async {
    try {
      final status = await _apiService.getSchedulerStatus();
      state = state.copyWith(schedulerStatus: status);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  // 加载报警列表
  Future<void> loadAlerts({bool unreadOnly = false}) async {
    try {
      final alerts =
          await _apiService.getAlerts(isRead: unreadOnly ? false : null);
      final unreadCount = alerts.where((a) => !a.isRead).length;
      state = state.copyWith(
        alerts: alerts,
        unreadCount: unreadCount,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  // 标记报警已读
  Future<void> markAsRead(String id) async {
    try {
      await _apiService.markAlertRead(id);
      final index = state.alerts.indexWhere((a) => a.id == id);
      if (index == -1) return;
      final newList = [...state.alerts];
      newList[index] = Alert(
        id: newList[index].id,
        subscriptionId: newList[index].subscriptionId,
        taskId: newList[index].taskId,
        sentimentScore: newList[index].sentimentScore,
        alertType: newList[index].alertType,
        isRead: true,
        createdAt: newList[index].createdAt,
      );
      state = state.copyWith(
        alerts: newList,
        unreadCount: state.unreadCount > 0 ? state.unreadCount - 1 : 0,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> markAllAsRead() async {
    try {
      await _apiService.markAllAlertsRead();
      final newList = state.alerts
          .map((alert) => Alert(
                id: alert.id,
                subscriptionId: alert.subscriptionId,
                taskId: alert.taskId,
                sentimentScore: alert.sentimentScore,
                alertType: alert.alertType,
                isRead: true,
                createdAt: alert.createdAt,
              ))
          .toList();
      state = state.copyWith(
        alerts: newList,
        unreadCount: 0,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  // 刷新所有数据
  Future<void> refresh() async {
    await Future.wait([
      loadSubscriptions(),
      loadAlerts(),
      loadSchedulerStatus(),
    ]);
  }
}

// Provider
final subscriptionProvider =
    StateNotifierProvider<SubscriptionNotifier, SubscriptionState>((ref) {
  final apiService = ref.watch(apiServiceProvider);
  return SubscriptionNotifier(apiService);
});

// 未读报警数Provider
final unreadAlertCountProvider = Provider<int>((ref) {
  return ref.watch(subscriptionProvider).unreadCount;
});
