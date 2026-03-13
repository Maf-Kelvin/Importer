// lib/presentation/themes/light_theme.dart
import 'package:flutter/material.dart';
import 'app_theme.dart';

class LightTheme {
  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        
        // Color scheme
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppTheme.primaryBlue,
          brightness: Brightness.light,
        ).copyWith(
          primary: AppTheme.primaryBlue,
          onPrimary: Colors.white,
          secondary: AppTheme.primaryBlueLight,
          surface: Colors.white,
          onSurface: AppTheme.neutral900,
          background: AppTheme.neutral50,
          onBackground: AppTheme.neutral900,
          error: AppTheme.errorRed,
          onError: Colors.white,
        ),

        // Typography
        textTheme: AppTheme.textTheme.apply(
          bodyColor: AppTheme.neutral900,
          displayColor: AppTheme.neutral900,
        ),

        // App bar theme
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: AppTheme.neutral900,
          elevation: 0,
          scrolledUnderElevation: 1,
          surfaceTintColor: Colors.transparent,
        ),

        // Card theme
        cardTheme: CardTheme(
          color: Colors.white,
          elevation: 1,
          shadowColor: AppTheme.neutral200,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),

        // Input decoration theme
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: AppTheme.neutral100,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 12,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.neutral300),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.neutral300),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.primaryBlue, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
            borderSide: const BorderSide(color: AppTheme.errorRed),
          ),
        ),

        // Elevated button theme
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.primaryBlue,
            foregroundColor: Colors.white,
            elevation: 0,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
        ),

        // Outlined button theme
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: AppTheme.primaryBlue,
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            side: const BorderSide(color: AppTheme.primaryBlue),
          ),
        ),

        // Text button theme
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            foregroundColor: AppTheme.primaryBlue,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          ),
        ),

        // Bottom navigation bar theme
        bottomNavigationBarTheme: const BottomNavigationBarTheme(
          backgroundColor: Colors.white,
          selectedItemColor: AppTheme.primaryBlue,
          unselectedItemColor: AppTheme.neutral500,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
        ),

        // Floating action button theme
        floatingActionButtonTheme: const FloatingActionButtonThemeData(
          backgroundColor: AppTheme.primaryBlue,
          foregroundColor: Colors.white,
        ),

        // Drawer theme
        drawerTheme: const DrawerThemeData(
          backgroundColor: Colors.white,
        ),

        // Scaffold background
        scaffoldBackgroundColor: AppTheme.neutral50,
      );
}
