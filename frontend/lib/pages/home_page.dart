import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/task_provider.dart';
import '../utils/constants.dart';
import '../widgets/app_background.dart';
import 'progress_page.dart';
import 'subscription_page.dart';
import 'task_history_page.dart';

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

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final _keywordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  Set<String> _selectedPlatforms = {'reddit', 'youtube'};
  Map<String, Map<String, dynamic>>? _platformConfigs;
  String _reportLanguage = 'auto';
  bool _semanticSamplingEnabled = false;

  @override
  void initState() {
    super.initState();
    final configs = _platformConfigsSafe;
    for (final platform in _selectedPlatforms) {
      configs[platform] = _defaultPlatformConfig(platform);
    }
  }

  @override
  void dispose() {
    _keywordController.dispose();
    super.dispose();
  }

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

  Map<String, Map<String, dynamic>> get _platformConfigsSafe {
    return _platformConfigs ??= <String, Map<String, dynamic>>{};
  }

  Map<String, dynamic> _buildPlatformConfigsPayload() {
    final payload = <String, dynamic>{};
    for (final platform in _selectedPlatforms) {
      payload[platform] = Map<String, dynamic>.from(
        _platformConfigsSafe[platform] ?? _defaultPlatformConfig(platform),
      );
    }
    return payload;
  }

  Future<void> _showPlatformConfigDialog(String platform) async {
    final title = AppConstants.platformNames[platform] ?? platform;
    final config = Map<String, dynamic>.from(
      _platformConfigsSafe[platform] ?? _defaultPlatformConfig(platform),
    );

    await showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          void update(String key, dynamic value, {bool notify = true}) {
            config[key] = value;
            if (notify) setDialogState(() {});
          }

          Widget buildForm() {
            if (platform == 'reddit') {
              final sortValue = _redditSortOptions.contains(config['sort'])
                  ? config['sort']
                  : _redditSortOptions.first;
              final timeValue = _redditTimeOptions.contains(config['time_filter'])
                  ? config['time_filter']
                  : _redditTimeOptions.first;
              final includeComments = config['include_comments'] == true;

              return Column(
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
                  const SizedBox(height: 12),
                  TextFormField(
                    initialValue: (config['subreddit'] ?? 'all').toString(),
                    decoration: const InputDecoration(labelText: 'Subreddit'),
                    onChanged: (value) => update('subreddit', value, notify: false),
                  ),
                  const SizedBox(height: 12),
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
                  const SizedBox(height: 12),
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
                  const SizedBox(height: 12),
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
                        if (parsed != null) {
                          update('comments_limit', parsed, notify: false);
                        }
                      },
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
              return Column(
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
                  const SizedBox(height: 12),
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
                      const SizedBox(height: 12),
                      TextFormField(
                        initialValue: languageValue,
                        decoration: const InputDecoration(labelText: '自定义语言代码'),
                        onChanged: (value) =>
                            update('transcript_language', value, notify: false),
                      ),
                    ],
                    const SizedBox(height: 12),
                    TextFormField(
                      initialValue: (config['segment_duration_sec'] ?? 300).toString(),
                      decoration: const InputDecoration(labelText: '切分间隔(秒)'),
                      keyboardType: TextInputType.number,
                      onChanged: (value) {
                        final parsed = int.tryParse(value);
                        if (parsed != null) {
                          update('segment_duration_sec', parsed, notify: false);
                        }
                      },
                    ),
                  ],
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

              return Column(
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
                  const SizedBox(height: 12),
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
                  const SizedBox(height: 12),
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
                    const SizedBox(height: 12),
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
              );
            }

            return TextFormField(
              initialValue: (config['limit'] ?? 10).toString(),
              decoration: const InputDecoration(labelText: '采集数量'),
              keyboardType: TextInputType.number,
              onChanged: (value) {
                final parsed = int.tryParse(value);
                if (parsed != null) update('limit', parsed, notify: false);
              },
            );
          }

          return AlertDialog(
            title: Text('$title 配置'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '仅影响本次任务的采集参数',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                  const SizedBox(height: 12),
                  buildForm(),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('取消'),
              ),
              FilledButton(
                onPressed: () {
                  setState(() {
                    _platformConfigsSafe[platform] = config;
                  });
                  Navigator.pop(context);
                },
                child: const Text('保存'),
              ),
            ],
          );
        },
      ),
    );
  }

  void _showSemanticSamplingInfo() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('智能采样技术说明'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '该功能利用本地轻量化向量模型 (Embedding) 对采集到的文本进行高维语义空间映射与聚类。',
                style: TextStyle(height: 1.5),
              ),
              const SizedBox(height: 16),
              const Text(
                '核心作用：',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              const Text('• 语义去重：自动过滤掉措辞不同但含义重复的灌水言论。\n'
                  '• 观点抽样：从每个观点聚类中抽取最具代表性的样本送入大模型分析。'),
              const SizedBox(height: 16),
              const Text(
                '💡 推荐场景：',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              const Text(
                '建议在【热门话题】或【数据量大】（如采集数>100）时开启。此时它能显著提升分析的广度与准确性。\n\n'
                '对于小样本数据，建议关闭以节省计算时间。',
                style: TextStyle(height: 1.5, color: Colors.black87),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('了解'),
          ),
        ],
      ),
    );
  }

  Widget _buildPlatformChip(String name) {
    final isSelected = _selectedPlatforms.contains(name);
    return GestureDetector(
      onDoubleTap: () => _showPlatformConfigDialog(name),
      child: Tooltip(
        message: '双击配置',
        child: FilterChip(
          label: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 24,
                height: 24,
                child: Center(
                  child: Text(
                    AppConstants.platformIcons[name] ?? '🌐',
                    style: const TextStyle(fontSize: 18, height: 1.0),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                name.toUpperCase(),
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 6,
          ),
          labelPadding: const EdgeInsets.symmetric(horizontal: 2),
          visualDensity: VisualDensity.compact,
          selected: isSelected,
          onSelected: (selected) {
            setState(() {
              if (selected) {
                _selectedPlatforms.add(name);
                _platformConfigsSafe.putIfAbsent(
                  name,
                  () => _defaultPlatformConfig(name),
                );
              } else {
                _selectedPlatforms.remove(name);
              }
            });
          },
        ),
      ),
    );
  }

  void _submitTask() {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedPlatforms.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请至少选择一个平台')),
      );
      return;
    }

    final platformConfigs = _buildPlatformConfigsPayload();
    final reportLanguage = _reportLanguage.trim().isEmpty ? 'auto' : _reportLanguage.trim();

    ref.read(taskProvider.notifier).createTask(
      keyword: _keywordController.text.trim(),
      platforms: _selectedPlatforms.toList(),
      reportLanguage: reportLanguage,
      semanticSampling: _semanticSamplingEnabled,
      platformConfigs: platformConfigs.isNotEmpty ? platformConfigs : null,
    );

    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ProgressPage()),
    );
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

  @override
  Widget build(BuildContext context) {
    final platforms = ref.watch(platformsProvider);
    final isCustomReportLanguage = !_reportLanguageOptions.contains(_reportLanguage);
    final reportLanguageDropdownValue = isCustomReportLanguage
        ? _reportLanguageCustomValue
        : _reportLanguage;

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('AI舆情分析'),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: '历史任务',
            icon: const Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const TaskHistoryPage()),
              );
            },
          ),
          IconButton(
            tooltip: '订阅管理',
            icon: const Icon(Icons.subscriptions_outlined),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const SubscriptionPage()),
              );
            },
          ),
        ],
      ),
      body: AppBackground(
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    '新建分析任务',
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '输入关键词，系统将自动从选定平台采集数据并生成AI分析报告',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.grey[700],
                    ),
                  ),
                  const SizedBox(height: 24),
                  Container(
                    padding: const EdgeInsets.all(18),
                    decoration: _sectionDecoration(context),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '关键词',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 10),
                        TextFormField(
                          controller: _keywordController,
                          decoration: const InputDecoration(
                            hintText: '例如：ChatGPT, AI, Tesla',
                            prefixIcon: Icon(Icons.search),
                          ),
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return '请输入关键词';
                            }
                            return null;
                          },
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final maxWidth = constraints.maxWidth;
                      final isWide = maxWidth >= 900;
                      const double gap = 12;
                      final double cardWidth = math.max(0, isWide
                          ? (maxWidth - gap * 2) / 3
                          : (maxWidth - gap) / 2);
                      const EdgeInsets cardPadding = EdgeInsets.all(10);
                      const EdgeInsets platformPadding = EdgeInsets.all(12);
                      const double captionSize = 12;
                      const double iconSize = 18;
                      final TextStyle titleStyle = TextStyle(
                        fontWeight: FontWeight.w600,
                      );
                      final TextStyle captionStyle = TextStyle(
                        color: Colors.grey[600],
                        fontSize: captionSize,
                      );

                      final semanticCard = SizedBox(
                        width: cardWidth,
                        child: Container(
                          constraints: const BoxConstraints(minHeight: 140),
                          padding: cardPadding,
                          decoration: _sectionDecoration(context),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.auto_awesome,
                                        size: iconSize,
                                        color: Theme.of(context).colorScheme.primary,
                                      ),
                                      const SizedBox(width: 6),
                                                                        Text(
                                                                          '智能采样',
                                                                          style: titleStyle,
                                                                        ),
                                                                        const Spacer(),
                                                                        IconButton(
                                                                          icon: Icon(Icons.info_outline, size: iconSize),
                                                                          tooltip: '智能采样说明',
                                                                          padding: EdgeInsets.zero,
                                                                          constraints: const BoxConstraints.tightFor(
                                                                            width: 28,
                                                                            height: 28,
                                                                          ),
                                                                          splashRadius: 16,
                                                                          onPressed: _showSemanticSamplingInfo,
                                                                        ),
                                                                      ],
                                                                    ),
                                                                    const SizedBox(height: 6),
                                                                    Text(
                                                                      '语义去重与观点抽样',
                                                                      style: captionStyle,
                                                                    ),                                ],
                              ),
                              Row(
                                children: [
                                  Text(
                                    _semanticSamplingEnabled
                                        ? '已开启'
                                        : '已关闭',
                                    style: TextStyle(
                                      color: _semanticSamplingEnabled
                                          ? Theme.of(context).colorScheme.primary
                                          : Colors.grey[600],
                                      fontWeight: FontWeight.w600,
                                      fontSize: captionSize,
                                    ),
                                  ),
                                  const Spacer(),
                                  Switch(
                                    value: _semanticSamplingEnabled,
                                    onChanged: (value) {
                                      setState(() =>
                                          _semanticSamplingEnabled = value);
                                    },
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      );

                      final reportLanguageCard = SizedBox(
                        width: cardWidth,
                        child: Container(
                          constraints: const BoxConstraints(minHeight: 140),
                          padding: cardPadding,
                          decoration: _sectionDecoration(context),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(
                                        Icons.translate,
                                        size: iconSize,
                                        color: Theme.of(context).colorScheme.primary,
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        '报告语言',
                                        style: titleStyle,
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 6),
                                  DropdownButtonFormField<String>(
                                    value: reportLanguageDropdownValue,
                                    isExpanded: true,
                                    isDense: true,
                                    decoration: InputDecoration(
                                      contentPadding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 8,
                                      ),
                                      labelText: '输出语言',
                                      labelStyle: TextStyle(fontSize: captionSize),
                                    ),
                                    style: TextStyle(fontSize: captionSize, color: Colors.black87),
                                    items: [
                                      const DropdownMenuItem(
                                        value: 'auto',
                                        child: Text('自动'),
                                      ),
                                      ..._reportLanguageOptions
                                          .where((opt) => opt != 'auto')
                                          .map(
                                            (opt) => DropdownMenuItem(
                                              value: opt,
                                              child: Text(opt),
                                            ),
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
                                          _reportLanguage = '';
                                        } else {
                                          _reportLanguage = value;
                                        }
                                      });
                                    },
                                  ),
                                ],
                              ),
                              Padding(
                                padding: const EdgeInsets.only(top: 12.0),
                                child: Text(
                                  isCustomReportLanguage
                                      ? '当前：自定义'
                                      : '当前：${_reportLanguage.isEmpty ? 'auto' : _reportLanguage}',
                                  style: captionStyle,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );

                      final platformCard = SizedBox(
                        width: isWide ? cardWidth : maxWidth,
                        child: Container(
                          constraints: const BoxConstraints(minHeight: 140),
                          padding: platformPadding,
                          decoration: _sectionDecoration(context),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Column(
                                mainAxisSize: MainAxisSize.min,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '选择平台',
                                    style: titleStyle,
                                  ),
                                  const SizedBox(height: 6),
                                  Builder(
                                    builder: (context) {
                                      final chips = platforms.when(
                                        data: (platformList) => Wrap(
                                          spacing: 10,
                                          runSpacing: 10,
                                          children: platformList
                                              .map(_buildPlatformChip)
                                              .toList(),
                                        ),
                                        loading: () => const Center(
                                          child: Padding(
                                            padding: EdgeInsets.symmetric(vertical: 12),
                                            child: CircularProgressIndicator(),
                                          ),
                                        ),
                                        error: (e, _) => Wrap(
                                          spacing: 10,
                                          runSpacing: 10,
                                          children: ['reddit', 'youtube', 'x']
                                              .map(_buildPlatformChip)
                                              .toList(),
                                        ),
                                      );

                                      return chips;
                                    },
                                  ),
                                ],
                              ),
                              Padding(
                                padding: const EdgeInsets.only(top: 12.0),
                                child: Text(
                                  '双击平台可配置采集参数',
                                  style: captionStyle,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );

                      final customLanguageCard = isCustomReportLanguage
                          ? Padding(
                              padding: const EdgeInsets.only(top: 12),
                              child: Container(
                                padding: const EdgeInsets.all(14),
                                decoration: _sectionDecoration(context),
                                child: TextFormField(
                                  initialValue: _reportLanguage,
                                  decoration:
                                      const InputDecoration(labelText: '自定义语言代码'),
                                  validator: (value) {
                                    if (value == null || value.trim().isEmpty) {
                                      return '请输入语言代码';
                                    }
                                    return null;
                                  },
                                  onChanged: (value) =>
                                      _reportLanguage = value.trim(),
                                ),
                              ),
                            )
                          : const SizedBox.shrink();

                      if (isWide) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            IntrinsicHeight(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  semanticCard,
                                  SizedBox(width: gap),
                                  reportLanguageCard,
                                  SizedBox(width: gap),
                                  platformCard,
                                ],
                              ),
                            ),
                            customLanguageCard,
                          ],
                        );
                      }

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          IntrinsicHeight(
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                semanticCard,
                                SizedBox(width: gap),
                                reportLanguageCard,
                              ],
                            ),
                          ),
                          customLanguageCard,
                          const SizedBox(height: 16),
                          platformCard,
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton.icon(
                    onPressed: _submitTask,
                    icon: const Icon(Icons.auto_graph),
                    label: const Text(
                      '开始分析',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
