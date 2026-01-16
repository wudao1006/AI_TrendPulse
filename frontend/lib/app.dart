import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'pages/home_page.dart';

class AISentimentApp extends StatelessWidget {
  const AISentimentApp({super.key});

  @override
  Widget build(BuildContext context) {
    final lightScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF0F5B5F),
      brightness: Brightness.light,
    ).copyWith(
      primary: const Color(0xFF0F5B5F),
      secondary: const Color(0xFFF59E0B),
      surface: const Color(0xFFF6F4F0),
      background: const Color(0xFFF2F4F7),
    );
    final darkScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF0F5B5F),
      brightness: Brightness.dark,
    );

    return MaterialApp(
      title: 'AI舆情分析',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: lightScheme,
        useMaterial3: true,
        scaffoldBackgroundColor: lightScheme.background,
        textTheme: GoogleFonts.manropeTextTheme().apply(
          bodyColor: lightScheme.onBackground,
          displayColor: lightScheme.onBackground,
        ),
        cardTheme: CardThemeData(
          elevation: 0,
          color: Colors.white.withOpacity(0.92),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: AppBarTheme(
          centerTitle: true,
          elevation: 0,
          backgroundColor: Colors.transparent,
          surfaceTintColor: Colors.transparent,
          titleTextStyle: GoogleFonts.manrope(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: lightScheme.onBackground,
          ),
          iconTheme: IconThemeData(color: lightScheme.onBackground),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: Colors.white.withOpacity(0.92),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide(color: Colors.grey.shade200),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide(color: Colors.grey.shade200),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: BorderSide(color: lightScheme.primary, width: 1.2),
          ),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
            ),
            side: BorderSide(color: lightScheme.primary.withOpacity(0.4)),
          ),
        ),
        chipTheme: ChipThemeData(
          backgroundColor: Colors.white.withOpacity(0.9),
          selectedColor: lightScheme.primary.withOpacity(0.12),
          labelStyle: TextStyle(color: lightScheme.onBackground),
          shape: StadiumBorder(
            side: BorderSide(color: lightScheme.primary.withOpacity(0.2)),
          ),
        ),
      ),
      darkTheme: ThemeData(
        colorScheme: darkScheme,
        useMaterial3: true,
        textTheme: GoogleFonts.manropeTextTheme(ThemeData.dark().textTheme),
      ),
      themeMode: ThemeMode.system,
      home: const HomePage(),
    );
  }
}
