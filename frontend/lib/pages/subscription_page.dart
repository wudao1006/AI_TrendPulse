import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/subscription.dart';
import '../providers/subscription_provider.dart';
import '../providers/task_provider.dart';
import '../utils/constants.dart';
import '../widgets/app_background.dart';

const List<String> _redditSortOptions = ['relevance', 'hot', 'new', 'top'];
const List<String> _redditTimeOptions = ['day', 'week', 'month', 'year', 'all'];
const List<String> _xSortOptions = ['top', 'latest'];
const List<int> _xReplyDepthOptions = [1, 2];
const List<String> _youtubeTranscriptLanguageOptions = [
  'all',
  'en',
  'zh-CN',
  'zh-Hans',
  'ja',
  'ko',
  'es',
  'fr',
  'de',
  'ru',
];
const String _youtubeTranscriptCustomValue = '__custom__';
const List<String> _reportLanguageOptions = [
  'auto',
  'zh',
  'en',
  'ja',
  'ko',
  'es',
  'fr',
  'de',
  'ru',
];
const String _reportLanguageCustomValue = '__custom_report_language__';

Map<String, dynamic> _defaultPlatformConfig(String platform) {
  switch (platform) {
    case 'reddit':
      return {
        'limit': 20,
        'subreddit': 'all',
        'sort': 'relevance',
        'time_filter': 'week',
        'include_comments': true,
        'comments_limit': 10,
      };
    case 'youtube':
      return {
        'limit': 10,
        'include_transcript': true,
        'transcript_language': 'en',
        'segment_duration_sec': 300,
      };
    case 'x':
      return {
        'limit': 20,
        'sort': 'top',
        'include_replies': true,
        'max_replies': 20,
        'reply_depth': 1,
      };
    default:
      return {'limit': 10};
  }
}

Map<String, Map<String, dynamic>> _buildPlatformConfigs(
  Set<String> platforms,
  Map<String, dynamic>? existing,
) {
  final result = <String, Map<String, dynamic>>{};
  for (final platform in platforms) {
    final base = _defaultPlatformConfig(platform);
    final saved = existing != null && existing[platform] is Map
        ? Map<String, dynamic>.from(existing[platform])
        : <String, dynamic>{};
    result[platform] = {...base, ...saved};
  }
  return result;
}

Widget _buildPlatformConfigEditor({
  required BuildContext context,
  required String platform,
  required Map<String, dynamic> config,
  required void Function(String key, dynamic value, {bool notify}) update,
}) {
  final title = AppConstants.platformNames[platform] ?? platform;
  if (platform == 'reddit') {
    final sortValue = _redditSortOptions.contains(config['sort'])
        ? config['sort']
        : _redditSortOptions.first;
    final timeValue = _redditTimeOptions.contains(config['time_filter'])
        ? config['time_filter']
        : _redditTimeOptions.first;
    final includeComments = config['include_comments'] == true;

    return ExpansionTile(
      title: Text('$title 配置'),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            children: [
              TextFormField(
                initialValue: (config['limit'] ?? 20).toString(),
                decoration: const InputDecoration(labelText: '采集数量'),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  final parsed = int.tryParse(value);
                  if (parsed != null) update('limit', parsed, notify: false);
                },
              ),
              TextFormField(
                initialValue: (config['subreddit'] ?? 'all').toString(),
                decoration: const InputDecoration(labelText: 'Subreddit'),
                onChanged: (value) => update('subreddit', value, notify: false),
              ),
              DropdownButtonFormField<String>(
                value: sortValue,
                decoration: const InputDecoration(labelText: '排序'),
                items: _redditSortOptions
                    .map((opt) => DropdownMenuItem(value: opt, child: Text(opt)))
                    .toList(),
                onChanged: (value) {
                  if (value != null) update('sort', value, notify: true);
                },
              ),
              DropdownButtonFormField<String>(
                value: timeValue,
                decoration: const InputDecoration(labelText: '时间范围'),
                items: _redditTimeOptions
                    .map((opt) => DropdownMenuItem(value: opt, child: Text(opt)))
                    .toList(),
                onChanged: (value) {
                  if (value != null) update('time_filter', value, notify: true);
                },
              ),
              SwitchListTile(
                value: includeComments,
                title: const Text('抓取评论'),
                onChanged: (value) => update('include_comments', value, notify: true),
              ),
              if (includeComments)
                TextFormField(
                  initialValue: (config['comments_limit'] ?? 10).toString(),
                  decoration: const InputDecoration(labelText: '评论数量'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) {
                    final parsed = int.tryParse(value);
                    if (parsed != null) update('comments_limit', parsed, notify: false);
                  },
                ),
            ],
          ),
        ),
      ],
    );
  }

  if (platform == 'youtube') {
    final includeTranscript = config['include_transcript'] == true;
    final languageValue = (config['transcript_language'] ?? 'en').toString();
    final isCustomLanguage = !_youtubeTranscriptLanguageOptions.contains(languageValue);
    final dropdownValue = isCustomLanguage
        ? _youtubeTranscriptCustomValue
        : languageValue;
    return ExpansionTile(
      title: Text('$title 配置'),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            children: [
              TextFormField(
                initialValue: (config['limit'] ?? 10).toString(),
                decoration: const InputDecoration(labelText: '采集数量'),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  final parsed = int.tryParse(value);
                  if (parsed != null) update('limit', parsed, notify: false);
                },
              ),
              SwitchListTile(
                value: includeTranscript,
                title: const Text('抓取字幕'),
                onChanged: (value) => update('include_transcript', value, notify: true),
              ),
              if (includeTranscript) ...[
                DropdownButtonFormField<String>(
                  value: dropdownValue,
                  decoration: const InputDecoration(labelText: '字幕语言'),
                  items: [
                    ..._youtubeTranscriptLanguageOptions.map(
                      (opt) => DropdownMenuItem(value: opt, child: Text(opt)),
                    ),
                    const DropdownMenuItem(
                      value: _youtubeTranscriptCustomValue,
                      child: Text('自定义'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    if (value == _youtubeTranscriptCustomValue) {
                      update('transcript_language', '', notify: true);
                    } else {
                      update('transcript_language', value, notify: true);
                    }
                  },
                ),
                if (isCustomLanguage) ...[
                  TextFormField(
                    initialValue: languageValue,
                    decoration: const InputDecoration(labelText: '自定义语言代码'),
                    onChanged: (value) =>
                        update('transcript_language', value, notify: false),
                  ),
                ],
                TextFormField(
                  initialValue: (config['segment_duration_sec'] ?? 300).toString(),
                  decoration: const InputDecoration(labelText: '切分间隔(秒)'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) {
                    final parsed = int.tryParse(value);
                    if (parsed != null) update('segment_duration_sec', parsed, notify: false);
                  },
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  if (platform == 'x') {
    final sortValue = _xSortOptions.contains(config['sort'])
        ? config['sort']
        : _xSortOptions.first;
    final includeReplies = config['include_replies'] == true;
    final depthValue = _xReplyDepthOptions.contains(config['reply_depth'])
        ? config['reply_depth']
        : _xReplyDepthOptions.first;

    return ExpansionTile(
      title: Text('$title 配置'),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            children: [
              TextFormField(
                initialValue: (config['limit'] ?? 20).toString(),
                decoration: const InputDecoration(labelText: '采集数量'),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  final parsed = int.tryParse(value);
                  if (parsed != null) update('limit', parsed, notify: false);
                },
              ),
              DropdownButtonFormField<String>(
                value: sortValue,
                decoration: const InputDecoration(labelText: '排序'),
                items: _xSortOptions
                    .map((opt) => DropdownMenuItem(value: opt, child: Text(opt)))
                    .toList(),
                onChanged: (value) {
                  if (value != null) update('sort', value, notify: true);
                },
              ),
              SwitchListTile(
                value: includeReplies,
                title: const Text('抓取评论'),
                onChanged: (value) => update('include_replies', value, notify: true),
              ),
              if (includeReplies) ...[
                TextFormField(
                  initialValue: (config['max_replies'] ?? 20).toString(),
                  decoration: const InputDecoration(labelText: '评论数量'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) {
                    final parsed = int.tryParse(value);
                    if (parsed != null) {
                      update('max_replies', parsed, notify: false);
                    }
                  },
                ),
                DropdownButtonFormField<int>(
                  value: depthValue,
                  decoration: const InputDecoration(labelText: '评论深度'),
                  items: _xReplyDepthOptions
                      .map((opt) => DropdownMenuItem(value: opt, child: Text('$opt')))
                      .toList(),
                  onChanged: (value) {
                    if (value != null) update('reply_depth', value, notify: true);
                  },
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  return ExpansionTile(
    title: Text('$title 配置'),
    children: [
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: TextFormField(
          initialValue: (config['limit'] ?? 10).toString(),
          decoration: const InputDecoration(labelText: '采集数量'),
          keyboardType: TextInputType.number,
          onChanged: (value) {
            final parsed = int.tryParse(value);
            if (parsed != null) update('limit', parsed, notify: false);
          },
        ),
      ),
    ],
  );
}

Future<void> _showSubscriptionDialog(
  BuildContext context,
  WidgetRef ref, {
  Subscription? subscription,
}) async {
  final isEdit = subscription != null;
  final keywordController =
      TextEditingController(text: subscription?.keyword ?? '');
  final intervalController = TextEditingController(
    text: (subscription?.intervalHours ?? 6).toString(),
  );
  final intervalMinutesController = TextEditingController(
    text: subscription?.intervalMinutes?.toString() ?? '',
  );
  var useMinutes = (subscription?.intervalMinutes ?? 0) > 0;
  final alertController = TextEditingController(
    text: (subscription?.alertThreshold ?? 30).toString(),
  );
  String reportLanguage = subscription?.reportLanguage ?? 'auto';
  bool semanticSamplingEnabled = subscription?.semanticSampling ?? false;
  final selectedPlatforms = <String>{
    ...?subscription?.platforms,
  };
  if (selectedPlatforms.isEmpty) {
    selectedPlatforms.addAll(['reddit', 'youtube']);
  }

  final platformConfigs =
      _buildPlatformConfigs(selectedPlatforms, subscription?.platformConfigs);

  await showDialog(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) {
        void updateConfig(String platform, String key, dynamic value,
            {bool notify = true}) {
          platformConfigs[platform] ??= _defaultPlatformConfig(platform);
          platformConfigs[platform]![key] = value;
          if (notify) setState(() {});
        }

        int resolveLimit() {
          var total = 0;
          for (final platform in selectedPlatforms) {
            final config = platformConfigs[platform] ?? _defaultPlatformConfig(platform);
            final limitValue = config['limit'];
            final parsed = limitValue is int
                ? limitValue
                : int.tryParse(limitValue?.toString() ?? '');
            if (parsed != null && parsed > 0) {
              total += parsed;
            }
          }
          if (total <= 0) return 50;
          return total < 10 ? 10 : total;
        }

        return AlertDialog(
          title: Text(isEdit ? '编辑订阅' : '添加订阅'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: keywordController,
                  decoration: const InputDecoration(
                    labelText: '关键词',
                    hintText: '输入要订阅的关键词',
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: _reportLanguageOptions.contains(reportLanguage)
                      ? reportLanguage
                      : _reportLanguageCustomValue,
                  decoration: const InputDecoration(labelText: '报告语言'),
                  items: [
                    const DropdownMenuItem(
                      value: 'auto',
                      child: Text('自动（跟随关键词语言）'),
                    ),
                    ..._reportLanguageOptions
                        .where((opt) => opt != 'auto')
                        .map(
                          (opt) => DropdownMenuItem(value: opt, child: Text(opt)),
                        ),
                    const DropdownMenuItem(
                      value: _reportLanguageCustomValue,
                      child: Text('自定义'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    setState(() {
                      if (value == _reportLanguageCustomValue) {
                        reportLanguage = '';
                      } else {
                        reportLanguage = value;
                      }
                    });
                  },
                ),
                if (!_reportLanguageOptions.contains(reportLanguage)) ...[
                  const SizedBox(height: 8),
                  TextFormField(
                    initialValue: reportLanguage,
                    decoration: const InputDecoration(labelText: '自定义语言代码'),
                    onChanged: (value) => reportLanguage = value.trim(),
                  ),
                ],
                const SizedBox(height: 12),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: semanticSamplingEnabled,
                  title: const Text('语义预选（本地 Embedding）'),
                  subtitle: Text(
                    '先在本地做语义聚类与代表抽样，再送入 LLM；提升覆盖度，耗时略增。',
                    style: TextStyle(color: Colors.grey[600], fontSize: 12),
                  ),
                  onChanged: (value) {
                    setState(() => semanticSamplingEnabled = value);
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: useMinutes ? 'minutes' : 'hours',
                  decoration: const InputDecoration(labelText: '调度单位'),
                  items: const [
                    DropdownMenuItem(value: 'hours', child: Text('小时')),
                    DropdownMenuItem(value: 'minutes', child: Text('分钟')),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    final toMinutes = value == 'minutes';
                    if (toMinutes != useMinutes) {
                      if (toMinutes) {
                        final hours = int.tryParse(intervalController.text);
                        if ((intervalMinutesController.text).isEmpty && hours != null) {
                          intervalMinutesController.text = (hours * 60).toString();
                        }
                      } else {
                        final minutes = int.tryParse(intervalMinutesController.text);
                        if (intervalController.text.isEmpty && minutes != null) {
                          intervalController.text = (minutes / 60).ceil().toString();
                        }
                      }
                      useMinutes = toMinutes;
                      setState(() {});
                    }
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: useMinutes ? intervalMinutesController : intervalController,
                  decoration: InputDecoration(
                    labelText: useMinutes ? '间隔分钟数' : '间隔小时数',
                  ),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: alertController,
                  decoration: const InputDecoration(labelText: '报警阈值'),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  children: ['reddit', 'youtube', 'x'].map((p) {
                    return FilterChip(
                      label: Text(
                        '${AppConstants.platformIcons[p]} ${AppConstants.platformNames[p]}',
                      ),
                      selected: selectedPlatforms.contains(p),
                      onSelected: (s) {
                        setState(() {
                          if (s) {
                            selectedPlatforms.add(p);
                            platformConfigs[p] ??= _defaultPlatformConfig(p);
                          } else {
                            selectedPlatforms.remove(p);
                            platformConfigs.remove(p);
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                ...selectedPlatforms.map((platform) {
                  final config =
                      platformConfigs[platform] ?? _defaultPlatformConfig(platform);
                  return _buildPlatformConfigEditor(
                    context: context,
                    platform: platform,
                    config: config,
                    update: (key, value, {bool notify = true}) {
                      updateConfig(platform, key, value, notify: notify);
                    },
                  );
                }).toList(),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () async {
                if (keywordController.text.isEmpty ||
                    selectedPlatforms.isEmpty) {
                  return;
                }

                final limit = resolveLimit();
                final interval = int.tryParse(intervalController.text) ?? 6;
                final intervalMinutes = useMinutes
                    ? int.tryParse(intervalMinutesController.text)
                    : null;
                final alert = int.tryParse(alertController.text) ?? 30;
                final normalizedReportLanguage =
                    reportLanguage.trim().isEmpty ? 'auto' : reportLanguage.trim();
                final configs = {
                  for (final p in selectedPlatforms)
                    p: platformConfigs[p] ?? _defaultPlatformConfig(p),
                };

                if (isEdit) {
                  await ref
                      .read(subscriptionProvider.notifier)
                      .updateSubscription(subscription!.id, {
                    'keyword': keywordController.text,
                    'platforms': selectedPlatforms.toList(),
                    'report_language': normalizedReportLanguage,
                    'semantic_sampling': semanticSamplingEnabled,
                    'limit': limit,
                    'interval_hours': useMinutes ? 0 : interval,
                    'interval_minutes': intervalMinutes,
                    'alert_threshold': alert,
                    'platform_configs': configs,
                  });
                } else {
                  final sub = SubscriptionCreate(
                    keyword: keywordController.text,
                    platforms: selectedPlatforms.toList(),
                    reportLanguage: normalizedReportLanguage,
                    semanticSampling: semanticSamplingEnabled,
                    limit: limit,
                    intervalHours: useMinutes ? 0 : interval,
                    intervalMinutes: intervalMinutes,
                    alertThreshold: alert,
                    platformConfigs: configs,
                  );
                  await ref
                      .read(subscriptionProvider.notifier)
                      .createSubscription(sub);
                }

                if (context.mounted) Navigator.pop(context);
              },
              child: Text(isEdit ? '保存' : '添加'),
            ),
          ],
        );
      },
    ),
  );
}

class SubscriptionPage extends ConsumerStatefulWidget {
  const SubscriptionPage({super.key});

  @override
  ConsumerState<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends ConsumerState<SubscriptionPage> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(subscriptionProvider.notifier).refresh());
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        extendBodyBehindAppBar: true,
        appBar: AppBar(
          title: const Text('订阅管理'),
          bottom: const TabBar(
            tabs: [
              Tab(text: '我的订阅'),
              Tab(text: '报警通知'),
            ],
          ),
        ),
        body: AppBackground(
          child: SafeArea(
            child: const TabBarView(
              children: [
                _SubscriptionList(),
                _AlertList(),
              ],
            ),
          ),
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () => _showSubscriptionDialog(context, ref),
          child: const Icon(Icons.add),
        ),
      ),
    );
  }
}

class _SubscriptionList extends ConsumerWidget {
  const _SubscriptionList();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(subscriptionProvider);

    if (state.isLoading && state.subscriptions.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.error != null && state.subscriptions.isEmpty) {
      return Center(child: Text('加载失败: ${state.error}'));
    }
    if (state.subscriptions.isEmpty) {
      return const Center(child: Text('暂无订阅，点击右下角添加'));
    }

    return ListView(
      children: [
        _SchedulerStatusCard(status: state.schedulerStatus),
        ...state.subscriptions
            .map((sub) => _SubscriptionCard(subscription: sub))
            .toList(),
      ],
    );
  }
}

class _SchedulerStatusCard extends StatelessWidget {
  final SchedulerStatus? status;

  const _SchedulerStatusCard({required this.status});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final statusText = _buildStatusText();
    final color = _buildStatusColor(theme);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Container(
        padding: const EdgeInsets.all(12),
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
        child: Row(
          children: [
            Icon(Icons.schedule, color: color),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                statusText,
                style: theme.textTheme.bodyMedium,
              ),
            ),
            if (status != null)
              Text(
                '任务数: ${status!.jobCount}',
                style: theme.textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
              ),
          ],
        ),
      ),
    );
  }

  String _buildStatusText() {
    if (status == null) return '调度器状态未知';
    if (!status!.schedulerEnabled) return '调度器已关闭';
    if (!status!.initialized) return '调度器未启动';
    if (!status!.lockAcquired) return '调度器锁未获取';
    return '调度器运行中';
  }

  Color _buildStatusColor(ThemeData theme) {
    if (status == null) return Colors.grey;
    if (!status!.schedulerEnabled) return Colors.orange;
    if (!status!.initialized || !status!.lockAcquired) return Colors.orange;
    return theme.colorScheme.primary;
  }
}

class _SubscriptionCard extends ConsumerStatefulWidget {
  final Subscription subscription;

  const _SubscriptionCard({required this.subscription});

  @override
  ConsumerState<_SubscriptionCard> createState() => _SubscriptionCardState();
}

class _SubscriptionCardState extends ConsumerState<_SubscriptionCard> {
  bool _isTriggering = false;

  String _formatInterval(Subscription sub) {
    final minutes = sub.intervalMinutes;
    if (minutes != null && minutes > 0) {
      return '每${minutes}分钟';
    }
    return '每${sub.intervalHours}小时';
  }

  String _formatNextRun(DateTime? nextRunAt) {
    if (nextRunAt == null) return '未调度';
    final now = DateTime.now();
    final diff = nextRunAt.difference(now);
    if (diff.isNegative) return '执行中...';
    if (diff.inMinutes < 60) return '${diff.inMinutes}分钟后';
    if (diff.inHours < 24) return '${diff.inHours}小时后';
    return '${diff.inDays}天后';
  }

  String _formatLastRun(DateTime? lastRunAt) {
    if (lastRunAt == null) return '从未执行';
    return '${lastRunAt.month}/${lastRunAt.day} ${lastRunAt.hour}:${lastRunAt.minute.toString().padLeft(2, '0')}';
  }

  String _formatDateTime(DateTime? value) {
    if (value == null) return '暂无';
    return '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')} '
        '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _triggerNow() async {
    setState(() => _isTriggering = true);
    final success = await ref.read(subscriptionProvider.notifier).triggerSubscription(widget.subscription.id);
    setState(() => _isTriggering = false);

    if (mounted) {
      if (success) {
        await ref.read(subscriptionProvider.notifier).refresh();
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(success ? '任务已触发' : '触发失败'),
          backgroundColor: success ? Colors.green : Colors.red,
        ),
      );
    }
  }

  void _editSubscription() {
    _showSubscriptionDialog(context, ref, subscription: widget.subscription);
  }

  void _showDeleteDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除订阅'),
        content: Text('确定要删除 "${widget.subscription.keyword}" 的订阅吗?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('取消')),
          FilledButton(
            onPressed: () {
              ref.read(subscriptionProvider.notifier).deleteSubscription(widget.subscription.id);
              Navigator.pop(context);
            },
            child: const Text('删除'),
          ),
        ],
      ),
    );
  }

  Future<void> _showJobInfo() async {
    final info =
        await ref.read(subscriptionProvider.notifier).getJobInfo(widget.subscription.id);
    if (!mounted) return;

    showDialog(
      context: context,
      builder: (context) {
        final scheduler = info?.scheduler;
        final schedulerStatus = scheduler == null
            ? '调度器状态未知'
            : !scheduler.schedulerEnabled
                ? '调度器已关闭'
                : !scheduler.initialized
                    ? '调度器未启动'
                    : !scheduler.lockAcquired
                        ? '调度器锁未获取'
                        : '调度器运行中';

        return AlertDialog(
          title: const Text('调度详情'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('状态: $schedulerStatus'),
              const SizedBox(height: 6),
              Text('最近执行: ${_formatDateTime(info?.lastRunAt)}'),
              const SizedBox(height: 6),
              Text('下次执行: ${_formatDateTime(info?.nextRunAt)}'),
              const SizedBox(height: 6),
              Text('任务ID: ${info?.job?.jobId ?? "暂无"}'),
              const SizedBox(height: 6),
              Text('触发器: ${info?.job?.trigger ?? "暂无"}'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('关闭'),
            ),
          ],
        );
      },
    );
  }

  void _showTrend() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) {
        return _TrendSheet(subscriptionId: widget.subscription.id);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final sub = widget.subscription;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
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
                    sub.keyword,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                Switch(
                  value: sub.isActive,
                  onChanged: (v) {
                    ref.read(subscriptionProvider.notifier).toggleSubscription(sub.id, v);
                  },
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${sub.platforms.map((p) => AppConstants.platformIcons[p]).join(' ')} · ${_formatInterval(sub)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(Icons.schedule, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  '下次执行: ${_formatNextRun(sub.nextRunAt)}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
                const SizedBox(width: 16),
                Icon(Icons.history, size: 14, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  '上次: ${_formatLastRun(sub.lastRunAt)}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: _showJobInfo,
                  icon: const Icon(Icons.info_outline, size: 18),
                  label: const Text('调度详情'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: _showTrend,
                  icon: const Icon(Icons.show_chart, size: 18),
                  label: const Text('趋势'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: _editSubscription,
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: const Text('编辑'),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  onPressed: _showDeleteDialog,
                  icon: const Icon(Icons.delete_outline, size: 18),
                  label: const Text('删除'),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: sub.isActive && !_isTriggering ? _triggerNow : null,
                  icon: _isTriggering
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.play_arrow, size: 18),
                  label: Text(_isTriggering ? '触发中...' : '立即执行'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _TrendSheet extends ConsumerWidget {
  final String subscriptionId;

  const _TrendSheet({required this.subscriptionId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final future = ref
        .read(apiServiceProvider)
        .getSubscriptionTrend(subscriptionId, limit: 10);

    return DraggableScrollableSheet(
      initialChildSize: 0.68,
      minChildSize: 0.45,
      maxChildSize: 0.9,
      builder: (context, controller) {
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.96),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: ListView(
            controller: controller,
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                '趋势概览',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              FutureBuilder<SubscriptionTrendResponse>(
                future: future,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  if (snapshot.hasError) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      child: Text('加载失败: ${snapshot.error}'),
                    );
                  }
                  final data = snapshot.data;
                  final points = data?.points ?? [];
                  if (points.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Center(child: Text('暂无趋势数据')),
                    );
                  }

                  final sentimentValues =
                      points.map((p) => p.sentimentScore.toDouble()).toList();
                  final heatValues =
                      points.map((p) => p.heatIndex.toDouble()).toList();
                  final rangeText =
                      '${_formatShortDate(points.first.analyzedAt)} - ${_formatShortDate(points.last.analyzedAt)}';

                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '最近 ${points.length} 次 · $rangeText',
                        style: TextStyle(color: Colors.grey[600], fontSize: 12),
                      ),
                      const SizedBox(height: 12),
                      _TrendChartCard(
                        title: '情感分',
                        latestValue: sentimentValues.last,
                        color: const Color(0xFF0F5B5F),
                        values: sentimentValues,
                      ),
                      const SizedBox(height: 12),
                      _TrendChartCard(
                        title: '热度分',
                        latestValue: heatValues.last,
                        color: const Color(0xFFF59E0B),
                        values: heatValues,
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }

  String _formatShortDate(DateTime value) {
    return '${value.month}/${value.day} ${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
  }
}

class _TrendChartCard extends StatelessWidget {
  final String title;
  final double latestValue;
  final Color color;
  final List<double> values;

  const _TrendChartCard({
    required this.title,
    required this.latestValue,
    required this.color,
    required this.values,
  });

  @override
  Widget build(BuildContext context) {
    final maxX = math.max(0, values.length - 1).toDouble();
    final interval = values.length <= 5 ? 1.0 : 2.0;
    final spots = List.generate(
      values.length,
      (index) => FlSpot(index.toDouble(), values[index].clamp(0, 100).toDouble()),
    );

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withOpacity(0.1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.04),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                title,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 8),
              Text(
                latestValue.toStringAsFixed(0),
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 140,
            child: LineChart(
              LineChartData(
                minX: 0,
                maxX: maxX,
                minY: 0,
                maxY: 100,
                gridData: FlGridData(
                  show: true,
                  horizontalInterval: 20,
                  verticalInterval: interval,
                  getDrawingHorizontalLine: (value) => FlLine(
                    color: Colors.grey.withOpacity(0.15),
                    strokeWidth: 1,
                  ),
                  getDrawingVerticalLine: (value) => FlLine(
                    color: Colors.grey.withOpacity(0.1),
                    strokeWidth: 1,
                  ),
                ),
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(
                  topTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  rightTitles: const AxisTitles(
                    sideTitles: SideTitles(showTitles: false),
                  ),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: 20,
                      reservedSize: 28,
                      getTitlesWidget: (value, meta) => Text(
                        value.toInt().toString(),
                        style: TextStyle(color: Colors.grey[600], fontSize: 10),
                      ),
                    ),
                  ),
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      interval: interval,
                      getTitlesWidget: (value, meta) => Text(
                        '${value.toInt() + 1}',
                        style: TextStyle(color: Colors.grey[600], fontSize: 10),
                      ),
                    ),
                  ),
                ),
                lineBarsData: [
                  LineChartBarData(
                    spots: spots,
                    isCurved: true,
                    color: color,
                    barWidth: 3,
                    dotData: FlDotData(show: values.length <= 10),
                    belowBarData: BarAreaData(
                      show: true,
                      color: color.withOpacity(0.12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertList extends ConsumerWidget {
  const _AlertList();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(subscriptionProvider);

    if (state.isLoading && state.alerts.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.error != null && state.alerts.isEmpty) {
      return Center(child: Text('加载失败: ${state.error}'));
    }
    if (state.alerts.isEmpty) {
      return const Center(child: Text('暂无报警'));
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8),
          child: TextButton(
            onPressed: () => ref.read(subscriptionProvider.notifier).markAllAsRead(),
            child: const Text('全部标记已读'),
          ),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: state.alerts.length,
            itemBuilder: (context, index) {
              final alert = state.alerts[index];
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: alert.isRead
                      ? Colors.white.withOpacity(0.92)
                      : Colors.red.shade50.withOpacity(0.92),
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
                child: ListTile(
                  leading: Icon(
                    Icons.warning_amber,
                    color: alert.isRead ? Colors.grey : Colors.red,
                  ),
                  title: Text('情感分数: ${alert.sentimentScore}'),
                  subtitle: Text('${alert.alertType} · ${_formatDate(alert.createdAt)}'),
                  trailing: !alert.isRead
                      ? TextButton(
                          onPressed: () => ref
                              .read(subscriptionProvider.notifier)
                              .markAsRead(alert.id),
                          child: const Text('标记已读'),
                        )
                      : null,
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  String _formatDate(DateTime dt) {
    return '${dt.month}/${dt.day} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
  }
}
