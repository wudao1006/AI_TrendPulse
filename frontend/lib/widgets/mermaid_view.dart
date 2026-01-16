import 'package:flutter/material.dart';
import 'mermaid_view_mobile.dart' if (dart.library.html) 'mermaid_view_web.dart';

class MermaidView extends StatelessWidget {
  final String code;

  const MermaidView({
    super.key,
    required this.code,
  });

  @override
  Widget build(BuildContext context) {
    return MermaidViewBody(code: code);
  }
}
