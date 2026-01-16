import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/task_provider.dart';
import '../widgets/app_background.dart';
import '../widgets/sentiment_gauge.dart';
import '../widgets/opinion_card.dart';
import '../widgets/mermaid_view.dart';
import 'raw_data_page.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskState = ref.watch(taskProvider);
    final task = taskState.currentTask;
    final result = taskState.analysisResult;

    if (task == null || result == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('分析结果')),
        body: const Center(child: Text('暂无数据')),
      );
    }

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: Text('${task.keyword} 分析报告'),
        actions: [
          IconButton(
            icon: const Icon(Icons.list),
            tooltip: '查看源数据',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => RawDataPage(taskId: task.id)),
              );
            },
          ),
        ],
      ),
      body: AppBackground(
        child: SafeArea(
          child: RefreshIndicator(
            onRefresh: () => ref.read(taskProvider.notifier).refresh(),
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final wide = constraints.maxWidth > 600;
                      final cards = [
                        _MetricCard(
                          title: '情感得分',
                          child: SentimentGauge(score: result.sentimentScore.toDouble()),
                        ),
                        _MetricCard(
                          title: '热度指数',
                          child: _buildHeatIndex(result.heatIndex),
                        ),
                      ];
                      if (!wide) {
                        return Column(
                          children: [
                            ...cards.map((card) => Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: card,
                                )),
                          ],
                        );
                      }
                      return Row(
                        children: [
                          Expanded(child: cards[0]),
                          const SizedBox(width: 12),
                          Expanded(child: cards[1]),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: '任务信息',
                    icon: Icons.info_outline,
                    child: Column(
                      children: [
                        _buildInfoRow('关键词', task.keyword),
                        _buildInfoRow('平台', task.platforms.join(', ').toUpperCase()),
                        _buildInfoRow('采集数量', '${result.totalItems}条'),
                        _buildInfoRow('分析时间', _formatDate(result.analyzedAt)),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: '核心观点',
                    icon: Icons.lightbulb_outline,
                    child: Column(
                      children: result.keyOpinions.asMap().entries.map((entry) {
                        return OpinionCard(
                          index: entry.key + 1,
                          opinion: entry.value,
                        );
                      }).toList(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: '分析摘要',
                    icon: Icons.summarize,
                    child: Text(
                      result.summary,
                      style: const TextStyle(fontSize: 14, height: 1.6),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (result.mermaidCode != null && result.mermaidCode!.isNotEmpty)
                    _SectionCard(
                      title: '思维导图',
                      icon: Icons.account_tree,
                      child: MermaidView(code: result.mermaidCode!),
                    ),
                  const SizedBox(height: 24),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => RawDataPage(taskId: task.id),
                              ),
                            );
                          },
                          icon: const Icon(Icons.storage),
                          label: const Text('查看源数据'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () {
                            ref.read(taskProvider.notifier).clearTask();
                            Navigator.popUntil(context, (route) => route.isFirst);
                          },
                          icon: const Icon(Icons.add),
                          label: const Text('新建任务'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeatIndex(double heatIndex) {
    final color = heatIndex > 70
        ? Colors.red
        : heatIndex > 40
            ? Colors.orange
            : Colors.green;

    return Column(
      children: [
        Text(
          heatIndex.toStringAsFixed(0),
          style: TextStyle(
            fontSize: 48,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.local_fire_department, color: color, size: 16),
            const SizedBox(width: 4),
            Text(
              _getHeatLevel(heatIndex),
              style: TextStyle(color: color),
            ),
          ],
        ),
      ],
    );
  }

  String _getHeatLevel(double heatIndex) {
    if (heatIndex > 70) return '高热度';
    if (heatIndex > 40) return '中热度';
    return '低热度';
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final Widget child;

  const _MetricCard({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _sectionDecoration(context),
      child: Column(
        children: [
          Text(
            title,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;

  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: _sectionDecoration(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const Divider(height: 20),
          child,
        ],
      ),
    );
  }
}

BoxDecoration _sectionDecoration(BuildContext context) {
  return BoxDecoration(
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
  );
}
