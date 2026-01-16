import 'package:flutter/material.dart';

class AppBackground extends StatelessWidget {
  final Widget child;

  const AppBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Color(0xFFF8F6F3),
            Color(0xFFEAF2F4),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Stack(
        children: [
          const _BackdropShape(
            alignment: Alignment(-0.9, -0.8),
            color: Color(0x33F59E0B),
            size: 220,
          ),
          const _BackdropShape(
            alignment: Alignment(0.9, -0.6),
            color: Color(0x3310B981),
            size: 180,
          ),
          const _BackdropShape(
            alignment: Alignment(0.7, 0.9),
            color: Color(0x330EA5E9),
            size: 240,
          ),
          Positioned.fill(child: child),
        ],
      ),
    );
  }
}

class _BackdropShape extends StatelessWidget {
  final Alignment alignment;
  final Color color;
  final double size;

  const _BackdropShape({
    required this.alignment,
    required this.color,
    required this.size,
  });

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Align(
        alignment: alignment,
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
            boxShadow: [
              BoxShadow(
                color: color,
                blurRadius: 90,
                spreadRadius: 10,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
