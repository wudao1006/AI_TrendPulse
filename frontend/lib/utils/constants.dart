import 'package:flutter/material.dart';

/// 应用常量
class AppConstants {
  /// 平台图标映射
  static const Map<String, String> platformIcons = {
    'reddit': '🔴',
    'youtube': '📺',
    'x': '𝕏',
  };

  /// 平台名称映射
  static const Map<String, String> platformNames = {
    'reddit': 'Reddit',
    'youtube': 'YouTube',
    'x': 'X (Twitter)',
  };

  /// 情感分数颜色
  static Color getSentimentColor(num score) {
    if (score >= 70) return const Color(0xFF4CAF50); // 绿色
    if (score >= 40) return const Color(0xFFFF9800); // 橙色
    return const Color(0xFFF44336); // 红色
  }

  /// 情感分数标签
  static String getSentimentLabel(num score) {
    if (score >= 80) return '非常正面';
    if (score >= 60) return '正面';
    if (score >= 40) return '中立';
    if (score >= 20) return '负面';
    return '非常负面';
  }
}
