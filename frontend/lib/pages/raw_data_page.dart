import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/task_provider.dart';
import '../utils/constants.dart';
import '../widgets/app_background.dart';

class RawDataPage extends ConsumerStatefulWidget {
  final String taskId;

  const RawDataPage({super.key, required this.taskId});

  @override
  ConsumerState<RawDataPage> createState() => _RawDataPageState();
}

class _RawDataPageState extends ConsumerState<RawDataPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final List<String> _tabs = ['全部', 'reddit', 'youtube', 'x'];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('原始数据'),
        bottom: TabBar(
          controller: _tabController,
          tabs: _tabs.map((tab) {
            if (tab == '全部') return const Tab(text: '全部');
            return Tab(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(AppConstants.platformIcons[tab] ?? ''),
                  const SizedBox(width: 4),
                  Text(AppConstants.platformNames[tab] ?? tab),
                ],
              ),
            );
          }).toList(),
        ),
      ),
      body: AppBackground(
        child: SafeArea(
          child: TabBarView(
            controller: _tabController,
            children: _tabs.map((tab) {
              final platform = tab == '全部' ? null : tab;
              return _DataList(taskId: widget.taskId, platform: platform);
            }).toList(),
          ),
        ),
      ),
    );
  }
}

class _DataList extends ConsumerWidget {
  final String taskId;
  final String? platform;

  const _DataList({required this.taskId, this.platform});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final params = RawDataParams(taskId: taskId, platform: platform);
    final dataAsync = ref.watch(rawDataProvider(params));

    return dataAsync.when(
      data: (response) {
        if (response.data.isEmpty) {
          return const Center(child: Text('暂无数据'));
        }

        return ListView.builder(
          itemCount: response.data.length,
          itemBuilder: (context, index) {
            final item = response.data[index];
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
              child: ListTile(
                leading: Text(
                  AppConstants.platformIcons[item.platform] ?? '',
                  style: const TextStyle(fontSize: 24),
                ),
                title: Text(
                  item.title ??
                      item.content?.substring(
                        0,
                        (item.content!.length > 50 ? 50 : item.content!.length),
                      ) ??
                      '无标题',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (item.author != null)
                      Text('@${item.author}', style: const TextStyle(fontSize: 12)),
                    Text(item.engagementText, style: const TextStyle(fontSize: 12)),
                  ],
                ),
                trailing: item.url != null
                    ? IconButton(
                        icon: const Icon(Icons.open_in_new),
                        onPressed: () => _openUrl(item.url!),
                      )
                    : null,
                onTap: () => _showDetail(context, item),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _showDetail(BuildContext context, dynamic item) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => SingleChildScrollView(
          controller: scrollController,
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (item.title != null)
                Text(item.title!, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(AppConstants.platformIcons[item.platform] ?? ''),
                  const SizedBox(width: 8),
                  if (item.author != null) Text('@${item.author}'),
                ],
              ),
              const SizedBox(height: 8),
              Text(item.engagementText),
              const Divider(height: 24),
              if (item.content != null) Text(item.content!, style: const TextStyle(height: 1.6)),
              const SizedBox(height: 16),
              if (item.url != null)
                FilledButton.icon(
                  onPressed: () => _openUrl(item.url!),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('查看原文'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
