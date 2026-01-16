import 'dart:convert';
import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class MermaidViewBody extends StatefulWidget {
  final String code;

  const MermaidViewBody({
    super.key,
    required this.code,
  });

  @override
  State<MermaidViewBody> createState() => _MermaidViewBodyState();
}

class _MermaidViewBodyState extends State<MermaidViewBody> {
  static int _viewCounter = 0;
  late final String _viewType;
  html.IFrameElement? _iframe;
  bool _isLoading = true;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _viewType = 'mindmap-view-${_viewCounter++}';
    ui.platformViewRegistry.registerViewFactory(_viewType, (int viewId) {
      final element = html.IFrameElement()
        ..style.border = '0'
        ..style.width = '100%'
        ..style.height = '100%'
        ..srcdoc = _buildHtml(widget.code);
      _iframe = element;
      element.onLoad.listen((_) {
        if (mounted) {
          setState(() => _isLoading = false);
        }
      });
      element.onError.listen((_) {
        if (mounted) {
          setState(() {
            _isLoading = false;
            _hasError = true;
          });
        }
      });
      return element;
    });
  }

  @override
  void didUpdateWidget(covariant MermaidViewBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.code != widget.code) {
      _iframe?.srcdoc = _buildHtml(widget.code);
      setState(() {
        _isLoading = true;
        _hasError = false;
      });
    }
  }

  String _buildHtml(String mermaidCode) {
    final markdownJson = jsonEncode(_buildMarkdown(mermaidCode));

    return '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/d3@7.9.0/dist/d3.min.js"></script>
  <script src="https://unpkg.com/markmap-lib@0.18.12/dist/browser/index.iife.js"></script>
  <script src="https://unpkg.com/markmap-view@0.18.12/dist/browser/index.js"></script>
  <style>
    :root {
      --bg-1: #f8fafc;
      --bg-2: #eef2f7;
      --bg-3: #fff7e6;
      --ink: #0f172a;
      --muted: #64748b;
      --panel: rgba(255, 255, 255, 0.88);
      --panel-border: rgba(148, 163, 184, 0.55);
      --shadow: rgba(15, 23, 42, 0.18);
    }
    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      background-color: var(--bg-1);
      background-image:
        radial-gradient(800px 500px at 8% 8%, rgba(14, 116, 144, 0.12), transparent 60%),
        radial-gradient(700px 520px at 92% 6%, rgba(234, 179, 8, 0.14), transparent 60%),
        radial-gradient(900px 620px at 85% 95%, rgba(59, 130, 246, 0.10), transparent 65%),
        linear-gradient(120deg, var(--bg-1) 0%, var(--bg-2) 55%, var(--bg-3) 100%);
      overflow: hidden;
      font-family: "Space Grotesk", "Noto Sans SC", "Noto Sans", "PingFang SC",
        "Microsoft YaHei", Arial, sans-serif;
      color: var(--ink);
    }
    #toolbar {
      position: fixed;
      top: 12px;
      right: 12px;
      display: flex;
      gap: 6px;
      z-index: 10;
      padding: 6px;
      border-radius: 12px;
      background: var(--panel);
      border: 1px solid var(--panel-border);
      box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
      backdrop-filter: blur(8px);
    }
    #toolbar button {
      border: 1px solid rgba(148, 163, 184, 0.6);
      background: #ffffff;
      color: var(--ink);
      border-radius: 10px;
      padding: 6px 11px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
      transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }
    #toolbar button:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 12px rgba(15, 23, 42, 0.12);
      border-color: rgba(59, 130, 246, 0.55);
    }
    #toolbar button:active {
      transform: translateY(0);
      box-shadow: 0 2px 4px rgba(15, 23, 42, 0.12);
    }
    #mindmap {
      width: 100%;
      height: 100%;
      opacity: 0;
      animation: fadeIn 0.6s ease 0.2s forwards;
    }
    @keyframes fadeIn {
      to { opacity: 1; }
    }
  </style>
</head>
  <body>
  <div id="toolbar">
    <button id="zoom-in">+</button>
    <button id="zoom-out">-</button>
    <button id="zoom-reset">重置</button>
  </div>
  <svg id="mindmap"></svg>
  <script>
    const markdown = $markdownJson;
    const isCompact = window.innerWidth < 720;
    const pad = isCompact ? '6px 10px' : '7px 12px';
    const rootFont = isCompact ? '16px' : '18px';
    const { Transformer, Markmap, deriveOptions } = window.markmap;
    const transformer = new Transformer();
    const safeMarkdown = markdown && markdown.trim() ? markdown : '- Mindmap';
    const { root } = transformer.transform(safeMarkdown);
    const options = {
      autoFit: true,
      duration: 450,
      zoom: true,
      pan: true,
      fitRatio: 0.96,
      maxInitialScale: 1.6,
      paddingX: isCompact ? 8 : 12,
      spacingHorizontal: isCompact ? 80 : 110,
      spacingVertical: isCompact ? 10 : 14,
      nodeMinHeight: isCompact ? 16 : 18,
      color: ['#0f766e', '#2563eb', '#f97316', '#16a34a', '#ca8a04'],
      style: `
        .markmap {
          font-family: "Space Grotesk", "Noto Sans SC", "Noto Sans", "PingFang SC",
            "Microsoft YaHei", Arial, sans-serif;
          color: #0f172a;
        }
        .markmap-foreign > div > div {
          background: rgba(255, 255, 255, 0.92);
          border: 1px solid rgba(148, 163, 184, 0.65);
          border-radius: 12px;
          padding: \${pad};
          box-shadow: 0 10px 18px rgba(15, 23, 42, 0.12);
          font-weight: 600;
          line-height: 1.35;
        }
        .markmap-node[data-depth="1"] .markmap-foreign > div > div {
          background: #0f172a;
          color: #f8fafc;
          border-color: #0b1220;
          font-weight: 700;
          font-size: \${rootFont};
        }
        .markmap-node[data-depth="2"] .markmap-foreign > div > div {
          font-weight: 700;
        }
        .markmap-link {
          stroke-opacity: 0.45;
        }
        .markmap-node circle {
          display: none;
        }
      `
    };
    const svg = document.getElementById('mindmap');
    const resolvedOptions = typeof deriveOptions === 'function' ? deriveOptions(options) : options;
    const mm = Markmap.create(svg, resolvedOptions, root);
    mm.fit();

    document.getElementById('zoom-in').onclick = () => mm.rescale(1.15);
    document.getElementById('zoom-out').onclick = () => mm.rescale(0.85);
    document.getElementById('zoom-reset').onclick = () => mm.fit();

    window.addEventListener('resize', () => mm.fit());
  </script>
</body>
</html>
''';
  }

  String _buildMarkdown(String mermaidCode) {
    final lines = mermaidCode.split('\n');
    final indentUnit = _inferIndentUnit(lines);
    final buffer = StringBuffer();

    for (final rawLine in lines) {
      final line = rawLine.trimRight();
      if (line.trim().isEmpty) continue;
      final trimmed = line.trim();
      if (trimmed == 'mindmap') continue;

      final indent = _leadingIndent(rawLine);
      var depth = indentUnit > 0 ? (indent ~/ indentUnit) : 0;
      var label = trimmed;
      if (label.startsWith('root((') && label.endsWith('))')) {
        label = label.substring(6, label.length - 2);
        depth = 0;
      }
      label = label.replaceAll(RegExp(r'\s+'), ' ').trim();
      if (label.startsWith('- ')) {
        label = label.substring(2).trim();
      }

      final text = label.isEmpty ? 'Node' : label;
      final indentPrefix = List.filled(depth, '  ').join();
      buffer.writeln('$indentPrefix- $text');
    }

    final result = buffer.toString().trimRight();
    return result.isEmpty ? '- Mindmap' : result;
  }

  int _leadingIndent(String line) {
    var count = 0;
    for (var i = 0; i < line.length; i++) {
      final ch = line.codeUnitAt(i);
      if (ch == 0x20) {
        count += 1;
      } else if (ch == 0x09) {
        count += 2;
      } else {
        break;
      }
    }
    return count;
  }

  int _inferIndentUnit(List<String> lines) {
    var minIndent = 0;
    for (final rawLine in lines) {
      final trimmed = rawLine.trim();
      if (trimmed.isEmpty || trimmed == 'mindmap') continue;
      final indent = _leadingIndent(rawLine);
      if (indent <= 0) continue;
      if (minIndent == 0 || indent < minIndent) {
        minIndent = indent;
      }
    }
    return minIndent == 0 ? 2 : minIndent;
  }

  void _setIframePointerEvents(bool enabled) {
    if (_iframe == null) return;
    _iframe!.style.pointerEvents = enabled ? 'auto' : 'none';
  }

  @override
  Widget build(BuildContext context) {
    if (_hasError) {
      return _buildFallbackView();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          height: 360,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[300]!),
            borderRadius: BorderRadius.circular(8),
          ),
          clipBehavior: Clip.antiAlias,
          child: Stack(
            children: [
              HtmlElementView(viewType: _viewType),
              if (_isLoading)
                const Center(
                  child: CircularProgressIndicator(),
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          alignment: WrapAlignment.end,
          spacing: 8,
          children: [
            TextButton.icon(
              onPressed: () => _showCodeDialog(context),
              icon: const Icon(Icons.code, size: 18),
              label: const Text('查看代码'),
            ),
            TextButton.icon(
              onPressed: () => _copyCode(),
              icon: const Icon(Icons.copy, size: 18),
              label: const Text('复制代码'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFallbackView() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[100],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[300]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber, color: Colors.orange[700], size: 20),
              const SizedBox(width: 8),
              const Text(
                '无法渲染思维导图',
                style: TextStyle(fontWeight: FontWeight.w500),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Mermaid代码:',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(6),
            ),
            child: SelectableText(
              widget.code,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              onPressed: () => _copyCode(),
              icon: const Icon(Icons.copy, size: 18),
              label: const Text('复制代码'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showCodeDialog(BuildContext context) async {
    _setIframePointerEvents(false);
    try {
      await showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Mermaid 代码'),
          content: SingleChildScrollView(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                widget.code,
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 12,
                ),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('关闭'),
            ),
            ElevatedButton.icon(
              onPressed: () {
                _copyCode();
                Navigator.pop(context);
              },
              icon: const Icon(Icons.copy, size: 18),
              label: const Text('复制'),
            ),
          ],
        ),
      );
    } finally {
      _setIframePointerEvents(true);
    }
  }

  void _copyCode() {
    Clipboard.setData(ClipboardData(text: widget.code));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('代码已复制到剪贴板'),
        duration: Duration(seconds: 2),
      ),
    );
  }
}
