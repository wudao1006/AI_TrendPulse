/// 核心观点
class KeyOpinion {
  final String title;
  final String description;
  final List<String> points;

  KeyOpinion({
    required this.title,
    required this.description,
    this.points = const [],
  });

  factory KeyOpinion.fromJson(Map<String, dynamic> json) {
    return KeyOpinion(
      title: json['title'],
      description: json['description'],
      points: (json['points'] as List?)?.map((e) => e.toString()).toList() ?? const [],
    );
  }
}

/// 分析结果
class AnalysisResult {
  final String taskId;
  final int sentimentScore;
  final List<KeyOpinion> keyOpinions;
  final String summary;
  final String? mermaidCode;
  final double heatIndex;
  final int totalItems;
  final Map<String, int> platformDistribution;
  final DateTime analyzedAt;

  AnalysisResult({
    required this.taskId,
    required this.sentimentScore,
    required this.keyOpinions,
    required this.summary,
    this.mermaidCode,
    required this.heatIndex,
    required this.totalItems,
    required this.platformDistribution,
    required this.analyzedAt,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      taskId: json['task_id'],
      sentimentScore: json['sentiment_score'],
      keyOpinions: (json['key_opinions'] as List)
          .map((item) => KeyOpinion.fromJson(item))
          .toList(),
      summary: json['summary'],
      mermaidCode: json['mermaid_code'],
      heatIndex: (json['heat_index'] as num).toDouble(),
      totalItems: json['total_items'],
      platformDistribution: Map<String, int>.from(
        (json['platform_distribution'] as Map).map(
          (key, value) => MapEntry(key.toString(), value as int),
        ),
      ),
      analyzedAt: DateTime.parse(json['analyzed_at']),
    );
  }
}
