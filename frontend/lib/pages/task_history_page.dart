import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../models/task.dart';
import '../providers/task_provider.dart';
import '../widgets/app_background.dart';
import 'dashboard_page.dart';
import 'progress_page.dart';

class TaskHistoryPage extends ConsumerStatefulWidget {
  const TaskHistoryPage({super.key});

  @override
  ConsumerState<TaskHistoryPage> createState() => _TaskHistoryPageState();
}

class _TaskHistoryPageState extends ConsumerState<TaskHistoryPage> {
  final int _pageSize = 20;
  int _page = 1;
  int _total = 0;
  bool _isLoading = true;
  bool _isLoadingMore = false;
  String? _error;
  final List<TaskSummary> _tasks = [];

  @override
  void initState() {
    super.initState();
    _loadTasks(refresh: true);
  }

  Future<void> _loadTasks({bool refresh = false}) async {
    if (refresh) {
      setState(() {
        _page = 1;
        _total = 0;
        _tasks.clear();
        _error = null;
        _isLoading = true;
      });
    } else {
      setState(() => _isLoadingMore = true);
    }

    try {
      final api = ref.read(apiServiceProvider);
      final response = await api.getTaskList(page: _page, pageSize: _pageSize);
      if (!mounted) return;
      setState(() {
        _total = response.total;
        _tasks.addAll(response.data);
        _page += 1;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  Future<void> _openTask(TaskSummary task) async {
    await ref.read(taskProvider.notifier).loadTask(
          task.taskId,
          limitCount: task.limitCount,
        );
    if (!mounted) return;
    final taskState = ref.read(taskProvider);
    if (taskState.error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(taskState.error!)),
      );
      return;
    }

    if (taskState.currentTask?.status == TaskStatus.completed &&
        taskState.analysisResult != null) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const DashboardPage()),
      );
    } else {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const ProgressPage()),
      );
    }
  }

  Future<void> _deleteTask(TaskSummary task) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除任务'),
        content: Text('确认删除「${task.keyword}」吗？相关数据将一并清除。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final api = ref.read(apiServiceProvider);
      await api.deleteTask(task.taskId);
      if (!mounted) return;
      setState(() {
        _tasks.removeWhere((item) => item.taskId == task.taskId);
        if (_total > 0) {
          _total -= 1;
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('任务已删除')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('删除失败: $e')),
      );
    }
  }

  String _formatDate(DateTime date) {
    return DateFormat('yyyy-MM-dd HH:mm').format(date);
  }

  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending:
        return Colors.grey;
      case TaskStatus.running:
        return Colors.blue;
      case TaskStatus.completed:
        return Colors.green;
      case TaskStatus.failed:
        return Colors.red;
    }
  }

  String _getStatusText(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending:
        return '等待中';
      case TaskStatus.running:
        return '进行中';
      case TaskStatus.completed:
        return '已完成';
      case TaskStatus.failed:
        return '失败';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('历史任务'),
      ),
      body: AppBackground(
        child: SafeArea(
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('加载失败: $_error'),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () => _loadTasks(refresh: true),
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }
    if (_tasks.isEmpty) {
      return const Center(child: Text('暂无历史任务'));
    }

    final canLoadMore = _tasks.length < _total;

    return RefreshIndicator(
      onRefresh: () => _loadTasks(refresh: true),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _tasks.length + (canLoadMore ? 1 : 0),
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          if (index >= _tasks.length) {
            return Center(
              child: _isLoadingMore
                  ? const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: CircularProgressIndicator(),
                    )
                  : TextButton(
                      onPressed: () => _loadTasks(),
                      child: const Text('加载更多'),
                    ),
            );
          }

          final task = _tasks[index];
          final statusColor = _getStatusColor(task.status);

          return InkWell(
            onTap: () => _openTask(task),
            borderRadius: BorderRadius.circular(18),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.92),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white.withOpacity(0.4)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 24,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          task.keyword,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          _getStatusText(task.status),
                          style: TextStyle(
                            color: statusColor,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      PopupMenuButton<String>(
                        tooltip: '更多操作',
                        onSelected: (value) {
                          if (value == 'delete') {
                            _deleteTask(task);
                          }
                        },
                        itemBuilder: (context) => [
                          const PopupMenuItem(
                            value: 'delete',
                            child: Text('删除'),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    task.platforms.map((p) => p.toUpperCase()).join(', '),
                    style: TextStyle(color: Colors.grey[700]),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _formatDate(task.createdAt),
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                      Text(
                        '${task.progress}%',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
