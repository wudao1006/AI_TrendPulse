import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/task_provider.dart';
import '../models/task.dart';
import '../widgets/app_background.dart';
import 'dashboard_page.dart';

class ProgressPage extends ConsumerWidget {
  const ProgressPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskState = ref.watch(taskProvider);
    final task = taskState.currentTask;

    // 任务完成时自动跳转到仪表盘
    ref.listen<TaskState>(taskProvider, (previous, next) {
      if (next.currentTask?.status == TaskStatus.completed &&
          next.analysisResult != null) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const DashboardPage()),
        );
      }
    });

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('任务进度'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () {
            ref.read(taskProvider.notifier).clearTask();
            Navigator.pop(context);
          },
        ),
      ),
      body: AppBackground(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (taskState.isLoading && task == null) ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 16),
                  const Text('正在创建任务...'),
                ] else if (taskState.error != null) ...[
                  Icon(
                    Icons.error_outline,
                    size: 64,
                    color: Colors.red[400],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '任务失败',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.red[400],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    taskState.error!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey[700]),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: () {
                      ref.read(taskProvider.notifier).clearTask();
                      Navigator.pop(context);
                    },
                    child: const Text('返回'),
                  ),
                ] else if (task != null) ...[
                  _buildProgressIndicator(task),
                  const SizedBox(height: 32),
                  _buildTaskInfo(task),
                  const SizedBox(height: 24),
                  _buildProgressSteps(task),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProgressIndicator(Task task) {
    final progress = task.progress / 100;
    final color = _getStatusColor(task.status);

    return SizedBox(
      width: 180,
      height: 180,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: 180,
            height: 180,
            child: CircularProgressIndicator(
              value: progress,
              strokeWidth: 12,
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${task.progress}%',
                style: const TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                _getStatusText(task.status),
                style: TextStyle(
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTaskInfo(Task task) {
    return Container(
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
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('关键词'),
              Text(
                task.keyword,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const Divider(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('平台'),
              Text(
                task.platforms.map((p) => p.toUpperCase()).join(', '),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSteps(Task task) {
    final steps = [
      {'title': '创建任务', 'threshold': 0},
      {'title': '数据采集中', 'threshold': 10},
      {'title': 'AI分析中', 'threshold': 50},
      {'title': '生成报告', 'threshold': 90},
      {'title': '完成', 'threshold': 100},
    ];

    return Column(
      children: steps.asMap().entries.map((entry) {
        final index = entry.key;
        final step = entry.value;
        final isCompleted = task.progress >= (step['threshold'] as int);
        final isActive = index < steps.length - 1 &&
            task.progress >= (step['threshold'] as int) &&
            task.progress < (steps[index + 1]['threshold'] as int);

        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isCompleted
                      ? Colors.green
                      : isActive
                          ? Colors.blue
                          : Colors.grey[300],
                ),
                child: isCompleted
                    ? const Icon(Icons.check, size: 16, color: Colors.white)
                    : isActive
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : null,
              ),
              const SizedBox(width: 12),
              Text(
                step['title'] as String,
                style: TextStyle(
                  fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  color: isCompleted || isActive ? Colors.black : Colors.grey,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
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
}
