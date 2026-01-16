/// 原始数据
class RawData {
  final String id;
  final String platform;
  final String contentType;
  final String? title;
  final String? content;
  final String? author;
  final String? url;
  final Map<String, dynamic> metrics;
  final DateTime? publishedAt;

  RawData({
    required this.id,
    required this.platform,
    required this.contentType,
    this.title,
    this.content,
    this.author,
    this.url,
    required this.metrics,
    this.publishedAt,
  });

  factory RawData.fromJson(Map<String, dynamic> json) {
    return RawData(
      id: json['id'],
      platform: json['platform'],
      contentType: json['content_type'],
      title: json['title'],
      content: json['content'],
      author: json['author'],
      url: json['url'],
      metrics: Map<String, dynamic>.from(json['metrics'] ?? {}),
      publishedAt: json['published_at'] != null
          ? DateTime.parse(json['published_at'])
          : null,
    );
  }

  /// 获取互动数展示文本
  String get engagementText {
    final parts = <String>[];
    if (metrics.containsKey('upvotes')) {
      parts.add('👍 ${metrics['upvotes']}');
    }
    if (metrics.containsKey('views')) {
      parts.add('👁 ${metrics['views']}');
    }
    if (metrics.containsKey('likes')) {
      parts.add('❤️ ${metrics['likes']}');
    }
    if (metrics.containsKey('num_comments')) {
      parts.add('💬 ${metrics['num_comments']}');
    }
    return parts.join(' · ');
  }
}

/// 原始数据列表响应
class RawDataListResponse {
  final int total;
  final int page;
  final int pageSize;
  final List<RawData> data;

  RawDataListResponse({
    required this.total,
    required this.page,
    required this.pageSize,
    required this.data,
  });

  factory RawDataListResponse.fromJson(Map<String, dynamic> json) {
    return RawDataListResponse(
      total: json['total'],
      page: json['page'],
      pageSize: json['page_size'],
      data: (json['data'] as List)
          .map((item) => RawData.fromJson(item))
          .toList(),
    );
  }
}
